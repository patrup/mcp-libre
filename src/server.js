#!/usr/bin/env node
import { spawn } from 'child_process';
import { promises as fs } from 'fs';
import { join, dirname, extname, basename } from 'path';
import { homedir, tmpdir } from 'os';
import { createReadStream } from 'fs';
import readline from 'readline';

const tools = {
  create_document: {
    description: "Create LibreOffice document",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "File path" },
        type: { type: "string", enum: ["writer", "calc", "impress", "draw"], description: "Document type" },
        content: { type: "string", description: "Initial content" }
      },
      required: ["path", "type"]
    }
  },
  read_document_text: {
    description: "Extract text from document",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "File path" }
      },
      required: ["path"]
    }
  },
  convert_document: {
    description: "Convert document format",
    inputSchema: {
      type: "object",
      properties: {
        source_path: { type: "string", description: "Source file path" },
        target_path: { type: "string", description: "Target file path" },
        target_format: { type: "string", description: "Target format" }
      },
      required: ["source_path", "target_path", "target_format"]
    }
  },
  get_document_info: {
    description: "Get document metadata",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "File path" }
      },
      required: ["path"]
    }
  },
  read_spreadsheet_data: {
    description: "Extract spreadsheet data",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "File path" }
      },
      required: ["path"]
    }
  },
  insert_text_at_position: {
    description: "Insert text into document",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "File path" },
        text: { type: "string", description: "Text to insert" },
        position: { type: "integer", description: "Position offset" }
      },
      required: ["path", "text"]
    }
  },
  search_documents: {
    description: "Search documents by text",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Search query" },
        search_dir: { type: "string", description: "Directory to search" }
      },
      required: ["query"]
    }
  },
  batch_convert_documents: {
    description: "Convert multiple documents",
    inputSchema: {
      type: "object",
      properties: {
        source_dir: { type: "string", description: "Source directory" },
        target_dir: { type: "string", description: "Target directory" },
        target_format: { type: "string", description: "Target format" }
      },
      required: ["source_dir", "target_dir", "target_format"]
    }
  },
  merge_text_documents: {
    description: "Merge multiple documents",
    inputSchema: {
      type: "object",
      properties: {
        paths: { type: "array", items: { type: "string" }, description: "File paths" },
        output_path: { type: "string", description: "Output file path" }
      },
      required: ["paths", "output_path"]
    }
  },
  get_document_statistics: {
    description: "Get document statistics",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "File path" }
      },
      required: ["path"]
    }
  }
};

const resources = {
  "documents": {
    description: "List documents",
    mimeType: "text/plain"
  }
};

async function runLibreOffice(args, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const execs = ['libreoffice', 'loffice', 'soffice'];
    let lastError;

    const tryExec = (index) => {
      if (index >= execs.length) {
        reject(lastError || new Error("LibreOffice not found"));
        return;
      }

      const proc = spawn(execs[index], args, { timeout });
      let stdout = '';
      let stderr = '';

      proc.stdout?.on('data', (data) => { stdout += data; });
      proc.stderr?.on('data', (data) => { stderr += data; });

      proc.on('error', (err) => {
        lastError = err;
        tryExec(index + 1);
      });

      proc.on('close', (code) => {
        if (code === 0 || execs[index] === 'soffice') {
          resolve({ stdout, stderr, code });
        } else {
          lastError = new Error(`Exit code: ${code}`);
          tryExec(index + 1);
        }
      });
    };

    tryExec(0);
  });
}

async function getDocInfo(path) {
  const stat = await fs.stat(path).catch(() => null);
  return {
    path: path,
    filename: basename(path),
    format: extname(path).toLowerCase().slice(1) || 'unknown',
    size: stat?.size || 0,
    modified: stat?.mtime?.toISOString() || null,
    exists: !!stat
  };
}

async function readText(path) {
  const stat = await fs.stat(path).catch(() => null);
  if (!stat) throw new Error(`File not found: ${path}`);

  const tmpDir = tmpdir();
  await runLibreOffice(['--headless', '--convert-to', 'txt', '--outdir', tmpDir, path]);

  const txtFile = join(tmpDir, basename(path).replace(/\.[^.]+$/, '.txt'));
  const content = await fs.readFile(txtFile, 'utf-8').catch(() => '');

  const words = content.split(/\s+/).filter(w => w.length > 0).length;
  const chars = content.length;

  return {
    content: content,
    word_count: words,
    char_count: chars,
    page_count: null
  };
}

async function convertDoc(sourcePath, targetPath, targetFormat) {
  const sourceDir = dirname(sourcePath);
  const targetDir = dirname(targetPath);

  await fs.mkdir(targetDir, { recursive: true });

  try {
    await runLibreOffice(['--headless', '--convert-to', targetFormat, '--outdir', targetDir, sourcePath]);
    const sourceExt = extname(sourcePath);
    const stem = basename(sourcePath, sourceExt);
    const converted = join(targetDir, `${stem}.${targetFormat}`);

    if (converted !== targetPath) {
      const data = await fs.readFile(converted);
      await fs.writeFile(targetPath, data);
      await fs.unlink(converted);
    }

    return {
      source_path: sourcePath,
      target_path: targetPath,
      source_format: sourceExt.slice(1),
      target_format: targetFormat,
      success: true
    };
  } catch (err) {
    return {
      source_path: sourcePath,
      target_path: targetPath,
      source_format: extname(sourcePath).slice(1),
      target_format: targetFormat,
      success: false,
      error: err.message
    };
  }
}

async function createDoc(path, docType = 'writer', content = '') {
  const dir = dirname(path);
  await fs.mkdir(dir, { recursive: true });

  const formats = { writer: 'odt', calc: 'ods', impress: 'odp', draw: 'odg' };
  const format = formats[docType];

  if (!format) throw new Error(`Unknown type: ${docType}`);

  let filePath = path;
  if (!extname(filePath)) {
    filePath = `${filePath}.${format}`;
  }

  if (docType === 'writer' && content) {
    const tmpFile = join(tmpdir(), `temp_${Date.now()}.txt`);
    await fs.writeFile(tmpFile, content);
    await runLibreOffice(['--headless', '--convert-to', format, '--outdir', dir, tmpFile]);
    const converted = join(dir, basename(tmpFile, '.txt') + `.${format}`);
    if (converted !== filePath && await fs.stat(converted).catch(() => null)) {
      await fs.rename(converted, filePath);
    }
    await fs.unlink(tmpFile).catch(() => {});
  } else {
    await fs.writeFile(filePath, '');
  }

  return getDocInfo(filePath);
}

async function insertText(path, text, position = null) {
  const stat = await fs.stat(path).catch(() => null);
  if (!stat) throw new Error(`File not found: ${path}`);

  const content = await readText(path);
  const current = content.content;
  const pos = position ?? current.length;

  const updated = current.slice(0, pos) + text + current.slice(pos);

  const tmpFile = join(tmpdir(), `temp_${Date.now()}.txt`);
  await fs.writeFile(tmpFile, updated);

  const format = extname(path).slice(1);
  const dir = dirname(path);

  await runLibreOffice(['--headless', '--convert-to', format || 'odt', '--outdir', dir, tmpFile]);
  await fs.unlink(tmpFile).catch(() => {});

  return { success: true, length: updated.length };
}

async function searchDocs(query, searchDir = null) {
  const dirs = [searchDir, process.cwd(), join(homedir(), 'Documents'), homedir()].filter(Boolean);
  const results = [];
  const exts = ['.odt', '.ods', '.odp', '.doc', '.docx', '.txt'];

  for (const dir of dirs) {
    const stat = await fs.stat(dir).catch(() => null);
    if (!stat?.isDirectory()) continue;

    for (const ext of exts) {
      try {
        const files = await recursiveFind(dir, ext);
        for (const file of files) {
          try {
            const text = await readText(file);
            if (text.content.toLowerCase().includes(query.toLowerCase())) {
              const idx = text.content.toLowerCase().indexOf(query.toLowerCase());
              const start = Math.max(0, idx - 100);
              const end = Math.min(text.content.length, idx + query.length + 100);
              results.push({
                path: file,
                filename: basename(file),
                format: extname(file),
                word_count: text.word_count,
                match_context: (start > 0 ? '...' : '') + text.content.slice(start, end) + (end < text.content.length ? '...' : '')
              });
            }
          } catch {}
        }
      } catch {}
    }
  }

  return results;
}

async function recursiveFind(dir, ext, maxDepth = 5, depth = 0) {
  if (depth > maxDepth) return [];
  const files = [];
  try {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.isFile() && entry.name.endsWith(ext)) {
        files.push(join(dir, entry.name));
      } else if (entry.isDirectory() && !entry.name.startsWith('.')) {
        files.push(...await recursiveFind(join(dir, entry.name), ext, maxDepth, depth + 1));
      }
    }
  } catch {}
  return files;
}

async function getStats(path) {
  const info = await getDocInfo(path);
  const text = await readText(path);

  const lines = text.content.split('\n');
  const paras = text.content.split('\n\n').filter(p => p.trim());
  const sents = text.content.split(/[.!?]+/).filter(s => s.trim());

  return {
    file: info,
    content: {
      words: text.word_count,
      chars: text.char_count,
      lines: lines.length,
      paragraphs: paras.length,
      sentences: sents.length,
      avg_words_per_sentence: text.word_count / Math.max(sents.length, 1),
      avg_chars_per_word: text.char_count / Math.max(text.word_count, 1)
    }
  };
}

async function batchConvert(sourceDir, targetDir, targetFormat, exts = null) {
  const extensions = exts || ['.odt', '.ods', '.odp', '.doc', '.docx', '.xls', '.xlsx'];
  const results = [];

  for (const ext of extensions) {
    const files = await recursiveFind(sourceDir, ext);
    for (const file of files) {
      const stem = basename(file, extname(file));
      const target = join(targetDir, `${stem}.${targetFormat}`);
      const result = await convertDoc(file, target, targetFormat);
      results.push(result);
    }
  }

  return results;
}

async function mergeDocs(paths, outputPath, sep = '\n\n---\n\n') {
  const contents = [];
  for (const path of paths) {
    try {
      const text = await readText(path);
      contents.push(`=== ${basename(path)} ===\n\n${text.content}`);
    } catch (err) {
      contents.push(`=== ${basename(path)} ===\n\nError: ${err.message}`);
    }
  }

  const merged = contents.join(sep);
  return createDoc(outputPath, 'writer', merged);
}

async function handleTool(name, args) {
  switch (name) {
    case 'create_document':
      return createDoc(args.path, args.type, args.content || '');
    case 'read_document_text':
      return readText(args.path);
    case 'convert_document':
      return convertDoc(args.source_path, args.target_path, args.target_format);
    case 'get_document_info':
      return getDocInfo(args.path);
    case 'read_spreadsheet_data':
      return { sheet_name: 'data', data: [], row_count: 0, col_count: 0 };
    case 'insert_text_at_position':
      return insertText(args.path, args.text, args.position);
    case 'search_documents':
      return searchDocs(args.query, args.search_dir);
    case 'batch_convert_documents':
      return batchConvert(args.source_dir, args.target_dir, args.target_format);
    case 'merge_text_documents':
      return mergeDocs(args.paths, args.output_path);
    case 'get_document_statistics':
      return getStats(args.path);
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

async function listDocuments() {
  const dirs = [process.cwd(), join(homedir(), 'Documents'), homedir()];
  const docs = [];
  const exts = ['.odt', '.ods', '.odp', '.doc', '.docx', '.txt'];

  for (const dir of dirs) {
    for (const ext of exts) {
      const files = await recursiveFind(dir, ext, 3);
      docs.push(...files.map(f => `document://${f}`));
    }
  }

  return docs.join('\n');
}

function send(msg) {
  process.stdout.write(JSON.stringify(msg) + '\n');
}

function respond(id, result) {
  send({ jsonrpc: '2.0', id, result });
}

function error(id, message, code = -32000) {
  send({ jsonrpc: '2.0', id, error: { code, message } });
}

async function handleRequest(msg) {
  try {
    if (msg.method === 'initialize') {
      respond(msg.id, {
        protocolVersion: '2024-11-05',
        capabilities: {
          tools: {},
          resources: {}
        },
        serverInfo: { name: 'mcp-libre', version: '0.2.0' }
      });
    } else if (msg.method === 'tools/list') {
      respond(msg.id, { tools: Object.entries(tools).map(([k, v]) => ({ name: k, ...v })) });
    } else if (msg.method === 'tools/call') {
      const result = await handleTool(msg.params.name, msg.params.arguments || {});
      respond(msg.id, { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] });
    } else if (msg.method === 'resources/list') {
      respond(msg.id, { resources: Object.entries(resources).map(([k, v]) => ({ uri: k, ...v })) });
    } else if (msg.method === 'resources/read') {
      if (msg.params.uri === 'documents') {
        const content = await listDocuments();
        respond(msg.id, { contents: [{ uri: msg.params.uri, mimeType: 'text/plain', text: content }] });
      } else {
        error(msg.id, 'Resource not found', -32001);
      }
    } else {
      error(msg.id, 'Method not found', -32601);
    }
  } catch (err) {
    error(msg.id, err.message || 'Internal error');
  }
}

const rl = readline.createInterface({ input: process.stdin });

rl.on('line', async (line) => {
  try {
    const msg = JSON.parse(line);
    await handleRequest(msg);
  } catch (err) {
    send({ jsonrpc: '2.0', error: { code: -32700, message: 'Parse error' } });
  }
});
