// Minimal fake OpenAI-compatible server for the e2e smoke test.
//
// The backend's trial extraction talks to this via the official `openai` SDK,
// which appends `/models` and `/chat/completions` to the configured base_url.
// We only need those two routes. The chat response is canned: a JSON *string*
// in `choices[0].message.content` (per the OpenAI wire format) that validates
// against the 8-field lung-embolism schema, with finish_reason "stop" so the
// backend records a `success` TrialResult.
import http from 'node:http'

const PORT = Number(process.env.FAKE_LLM_PORT || 9099)
const HOST = '127.0.0.1'

// Any schema-valid combination works — accuracy vs. ground truth is irrelevant
// to the smoke, which only asserts that an evaluation is produced.
const EXTRACTION = {
  'shortness of breath': false,
  'chest pain': true,
  'leg pain or swelling': false,
  'heart palpitations': false,
  cough: false,
  dizziness: false,
  location: 'unknown',
  side: 'left',
}

const server = http.createServer((req, res) => {
  const send = (code, body) => {
    const payload = JSON.stringify(body)
    res.writeHead(code, {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload),
    })
    res.end(payload)
  }

  const url = req.url || ''

  if (req.method === 'GET' && url.endsWith('/models')) {
    send(200, {
      object: 'list',
      data: [{ id: 'fake-model', object: 'model', created: 0, owned_by: 'fake' }],
    })
    return
  }

  if (req.method === 'POST' && url.endsWith('/chat/completions')) {
    // Drain and ignore the request body — the reply is canned.
    req.on('data', () => {})
    req.on('end', () => {
      send(200, {
        id: 'chatcmpl-fake',
        object: 'chat.completion',
        created: 0,
        model: 'fake-model',
        choices: [
          {
            index: 0,
            finish_reason: 'stop',
            message: { role: 'assistant', content: JSON.stringify(EXTRACTION) },
          },
        ],
        usage: { prompt_tokens: 10, completion_tokens: 20, total_tokens: 30 },
      })
    })
    return
  }

  send(404, { error: { message: `fake-llm: unhandled ${req.method} ${url}` } })
})

server.listen(PORT, HOST, () => {
  console.log(`[fake-llm] listening on http://${HOST}:${PORT}`)
})
