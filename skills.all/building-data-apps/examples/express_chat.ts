// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// express_chat.ts
// requires: npm install express
// cors @google-cloud/geminidataanalytics @google-cloud/bigquery dotenv
import {DataChatServiceClient} from '@google-cloud/geminidataanalytics/build/src/v1beta';
import cors from 'cors';
import 'dotenv/config';
import express from 'express';

const app = express();
app.use(cors());
app.use(express.json());

const chatClient = new DataChatServiceClient();
const PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT || '<PROJECT_ID>';

app.post('/api/chat', async (req, res) => {
  const {message, history} = req.body;

  // Initialize SSE streaming headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const formattedHistory = [];
  if (history && Array.isArray(history)) {
    for (const msg of history) {
      if (msg.role === 'user') {
        formattedHistory.push({userMessage: {text: msg.content}});
      } else if (msg.role === 'model') {
        formattedHistory.push({systemMessage: {text: {parts: [msg.content]}}});
      }
    }
  }

  // Append new user message
  formattedHistory.push({userMessage: {text: message}});

  try {
    const chatRequest = {
      parent: `projects/${PROJECT_ID}/locations/us`,
      messages: formattedHistory,
      inlineContext: {
        systemInstruction:
          'You are a friendly data analytics assistant. Write SQL against BigQuery to answer user questions.',
        datasourceReferences: {
          bq: {
            tableReferences: [
              {
                projectId: PROJECT_ID,
                datasetId: '<BIGQUERY_DATASET>',
                tableId: '<BIGQUERY_TABLE>',
              },
            ],
          },
        },
        // Optionally disable plotting logic
        options: {chart: {}},
      },
    };

    const stream = chatClient.chat(chatRequest);

    stream.on('data', (response) => {
      const sysMsg = response.systemMessage;
      if (!sysMsg) return;

      // Emit Interactive Suggestions (Buttons)
      if (sysMsg.suggestions && sysMsg.suggestions.length > 0) {
        for (const suggestion of sysMsg.suggestions) {
          res.write(
            `data: ${JSON.stringify({
              type: 'SUGGESTION',
              content: suggestion.title,
            })}\n\n`,
          );
        }
      }

      // Detect Context (THOUGHT) vs Output (FINAL_RESPONSE) or newly formed Suggestions
      if (sysMsg.text && sysMsg.text.parts) {
        // Flexible textType checking to catch both top-level and nested enum numbers or strings
        const typeValue = sysMsg.textType ?? sysMsg.text.textType;

        // Suggestions are streamed as an array of parts with TEXT_TYPE_UNSPECIFIED at the very end
        if (
          typeValue === 'TEXT_TYPE_UNSPECIFIED' ||
          typeValue === 'UNSPECIFIED' ||
          typeValue === 0
        ) {
          for (const suggestion of sysMsg.text.parts) {
            if (suggestion && suggestion.trim()) {
              res.write(
                `data: ${JSON.stringify({type: 'SUGGESTION', content: suggestion.trim()})}\n\n`,
              );
            }
          }
        } else {
          const textContent = sysMsg.text.parts.join('\n');
          let evtType = 'FINAL_RESPONSE';

          if (
            typeValue === 'TEXT_TYPE_THOUGHT' ||
            typeValue === 'THOUGHT' ||
            typeValue === 1
          ) {
            evtType = 'THOUGHT';
          }

          res.write(
            `data: ${JSON.stringify({
              type: evtType,
              content: textContent,
            })}\n\n`,
          );
        }
      }
    });

    stream.on('end', () => {
      res.write('data: [DONE]\n\n');
      res.end();
    });

    stream.on('error', (err) => {
      console.error('Gemini API Error:', err);
      // Fallback response inside the API error
      res.write(
        `data: ${JSON.stringify({
          type: 'FINAL_RESPONSE',
          content: '\\n\\n**API Error**: ' + err.message,
        })}\n\n`,
      );
      res.write('data: [DONE]\n\n');
      res.end();
    });
  } catch (error) {
    console.error('Failure Setting Up Chat:', error);
    res.write(
      `data: ${JSON.stringify({
        type: 'FINAL_RESPONSE',
        content: 'Connection failed.',
      })}\n\n`,
    );
    res.write('data: [DONE]\n\n');
    res.end();
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Express chat running on port ${PORT}`);
});
