/*
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';

export async function createNotebook(directory: string, filename: string) {
  try {
    const extension = 'ipynb';
    const fullFilename = filename.endsWith(`.${extension}`)
      ? filename
      : `${filename}.${extension}`;

    const notebookPath = path.join(directory, fullFilename);
    const resolvedPath = path.resolve(notebookPath);
    const allowedBase = path.resolve(process.cwd());
    if (!resolvedPath.startsWith(allowedBase + path.sep) && resolvedPath !== allowedBase) {
      throw new Error('Invalid directory or filename: path traversal detected');
    }

    // Check if file already exists
    try {
      await fs.stat(notebookPath);
      throw new Error(`Notebook already exists at ${notebookPath}`);
    } catch (err: any) {
      // File doesn't exist - this is what we want
      if (err.code !== 'ENOENT') {
        throw err;
      }
    }

    const minimalNotebook = {
      cells: [],
      metadata: {},
      nbformat: 4,
      nbformat_minor: 2
    };

    await fs.writeFile(notebookPath, JSON.stringify(minimalNotebook, null, 2), 'utf8');

    return {
      success: true,
      message: `Created Jupyter notebook at ${notebookPath}`,
      notebookPath: notebookPath
    };
  } catch (error: any) {
    throw new Error(`Failed to create notebook: ${error.message}`);
  }
}
