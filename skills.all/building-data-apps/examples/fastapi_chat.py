# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from google.cloud import geminidataanalytics_v1beta as gemini
from pydantic import BaseModel

app = FastAPI()
client = gemini.DataChatServiceClient()
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "<PROJECT_ID>")


class ChatRequestModel(BaseModel):
  message: str
  history: list[dict] = []


@app.post("/api/chat")
async def chat(request: ChatRequestModel):
  """Handles chat requests by streaming responses from the Gemini DataChat API.

  Args:
    request: A ChatRequestModel containing the user's message and chat history.

  Returns:
    A StreamingResponse object that yields server-sent events.
  """
  # CRITICAL: inline_context MUST include datasource_references
  inline_context = {
      "system_instruction": (
          "You are a fraud analyst assistant. You can write SQL to analyze the"
          " BigQuery table."
      ),
      "datasource_references": {
          "bq": {
              "table_references": [{
                  "project_id": PROJECT_ID,
                  "dataset_id": "<BIGQUERY_DATASET>",
                  "table_id": "<BIGQUERY_TABLE>",
              }]
          }
      },
      "options": {"chart": {}},  # Prevents chart generation
  }

  client_history = []
  for msg in request.history:
    if msg.get("role") == "user":
      client_history.append(
          gemini.Message(
              user_message=gemini.UserMessage(text=msg.get("content"))
          )
      )
    elif msg.get("role") == "model":
      client_history.append(
          gemini.Message(
              system_message=gemini.SystemMessage(
                  text=gemini.TextMessage(parts=[msg.get("content")])
              )
          )
      )

  chat_request = gemini.ChatRequest(
      parent=f"projects/{PROJECT_ID}/locations/us",
      messages=client_history
      + [gemini.Message(user_message=gemini.UserMessage(text=request.message))],
      inline_context=inline_context,
  )

  def event_generator():
    try:
      # DataChatServiceClient.chat is automatically a streaming call
      response_stream = client.chat(request=chat_request)
      for chunk in response_stream:
        sys_msg = chunk.system_message
        if not sys_msg:
          continue

        # Stream interactive follow-up suggestions
        if sys_msg.suggestions:
          for s in sys_msg.suggestions:
            yield (
                "data: "
                f"{json.dumps({'type': 'SUGGESTION', 'content': s.title})}"
                "\n\n"
            )

        # Stream text chunks, identifying if it's a thought context or final
        # response
        if sys_msg.text and sys_msg.text.parts:
          raw_type = getattr(sys_msg, "text_type", None) or getattr(
              sys_msg.text, "text_type", None
          )
          type_name = (
              getattr(raw_type, "name", str(raw_type))
              if raw_type is not None
              else ""
          )

          # Suggestions are streamed as an array of parts with
          # TEXT_TYPE_UNSPECIFIED at the very end
          if "UNSPECIFIED" in type_name or raw_type == 0:
            for suggestion in sys_msg.text.parts:
              if suggestion and suggestion.strip():
                yield (
                    "data: "
                    f"{json.dumps({'type': 'SUGGESTION', 'content': suggestion.strip()})}"
                    "\n\n"
                )
          else:
            text_content = "".join(sys_msg.text.parts)
            evt_type = "FINAL_RESPONSE"

            if "THOUGHT" in type_name or str(raw_type) == "1":
              evt_type = "THOUGHT"

            yield (
                "data:"
                f" {json.dumps({'type': evt_type, 'content': text_content})}\n\n"
            )

      yield "data: [DONE]\n\n"
    except Exception as e:
      error_content = f"\\n\\n**API Error**: {str(e)}"
      error_dict = {"type": "FINAL_RESPONSE", "content": error_content}
      yield "data: " + json.dumps(error_dict) + "\n\n"
      yield "data: [DONE]\n\n"

  # Return as Server-Sent Events stream
  return StreamingResponse(event_generator(), media_type="text/event-stream")
