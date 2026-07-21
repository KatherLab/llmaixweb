// Realistic fake OpenAI-compatible server for the documentation-screenshot run.
//
// Unlike the e2e smoke's fake LLM (one canned answer for every document), this
// one returns a *per-document* extraction that actually matches each report's
// content, keyed by the patient's Medical Record Number parsed from the prompt.
// Each record carries the real `result`, the model's `reasoning`, and real token
// `usage` from an exported GPT-OSS-120B trial over backend/tests/files — mostly
// correct vs. ground truth with a handful of single-field errors — so the Trials
// and Evaluation screenshots (incl. the Reasoning panel and token counts) look
// believable instead of uniform.
//
// Baked in (not read from disk) so the screenshot run has no external data
// dependency. Serves only GET /models and POST /chat/completions.
import http from 'node:http'

const PORT = Number(process.env.FAKE_LLM_PORT || 9099)
const HOST = '127.0.0.1'

// MRN -> { result, reasoning, usage }, from a real GPT-OSS-120B trial over the 8
// sample reports. A few rows intentionally disagree with ground truth (side,
// location, heart palpitations, dizziness) to keep the evaluation realistic.
const DOCS = {
  1122334: {
    result: {
      'shortness of breath': true,
      'chest pain': false,
      'leg pain or swelling': true,
      'heart palpitations': false,
      cough: true,
      dizziness: true,
      location: 'segmental',
      side: 'left',
    },
    reasoning:
      "We need to parse the report and set booleans.\n\nSymptoms:\n\n- persistent cough: yes => cough true\n- difficulty breathing: that's shortness of breath => true\n\n- dizziness and lightheadedness: dizziness true\n\n- mild left leg swelling: leg pain or swelling true\n\n- chest pain: not mentioned, false\n\n- heart palpitations: not mentioned, false\n\nLocation: pulmonary embolism in the left lower lobe. That's segmental? Lower lobe is segmental level? The categories: main, segmental, unknown. Pulmonary embolism location is left lower lobe, that's a segmental branch (segmental pulmonary artery). So location = segmental.\n\nSide: left (PE in left lower lobe, left leg swelling). So side = left.\n\nReturn JSON.\n\nCheck any nuance: There's left leg swelling; side should reflect laterality of the issue? The side field likely for side of embolism? Use left.\n\nThus output JSON.\n\n",
    usage: {
      prompt_tokens: 808,
      completion_tokens: 273,
      total_tokens: 1081,
    },
  },
  1342576: {
    result: {
      'shortness of breath': true,
      'chest pain': true,
      'leg pain or swelling': true,
      'heart palpitations': false,
      cough: false,
      dizziness: false,
      location: 'segmental',
      side: 'right',
    },
    reasoning:
      'We need to extract boolean presence of symptoms.\n\nDocument: presenting symptoms: progressive dyspnea (shortness of breath) -> true. chest tightness described as chest tightness, likely chest pain? chest tightness is a type of chest pain. So chest pain true. leg pain or swelling: there is mild swelling observed in left leg, likely true. heart palpitations: not mentioned. false. cough: not mentioned. false. dizziness: not mentioned. false.\n\nLocation: need to pick main, segmental, unknown based on embolism location. CTPA showing pulmonary embolism in the right upper lobe. That\'s a segmental? Upper lobe could be lobar; main pulmonary artery would be main; segmental is smaller. Upper lobe embolism is likely lobar, not main or segmental. Since options only main, segmental, unknown, we may interpret "right upper lobe" as segmental (since lobar comprises segmental). Could be "segmental". Perhaps best to choose "segmental". The side: for embolism side is right (right upper lobe). So side = "right". Return JSON.\n\nCheck: leg swelling left leg, but side likely for PE location. They want side of the finding? Probably side of the embolism. So "right". So final JSON:\n\n{\n  "shortness of breath": true,\n  "chest pain": true,\n  "leg pain or swelling": true,\n  "heart palpitations": false,\n  "cough": false,\n  "dizziness": false,\n  "location": "segmental",\n  "side": "right"\n}\n\nReturn.',
    usage: {
      prompt_tokens: 897,
      completion_tokens: 416,
      total_tokens: 1313,
    },
  },
  2123242: {
    result: {
      'shortness of breath': true,
      'chest pain': true,
      'leg pain or swelling': false,
      'heart palpitations': false,
      cough: false,
      dizziness: false,
      location: 'unknown',
      side: 'bilateral',
    },
    reasoning:
      'We need to read the document and extract booleans for various symptoms, plus location and side.\n\nDocument: Patient diagnosed with lung embolism (fat embolism syndrome affecting both lungs). Presenting symptoms: sudden onset of shortness of breath, chest pain, and confusion. No leg swelling. No mention of heart palpitations, cough, dizziness (though confusion perhaps but not dizziness). So:\n\nshortness of breath: true\nchest pain: true\nleg pain or swelling: false (they said no leg swelling)\nheart palpitations: false (not mentioned)\ncough: false (not mentioned)\ndizziness: false (not mentioned; confusion is present but not dizziness)\n\nLocation: The location of the embolism? The schema expects "main", "segmental", "unknown". From report: "fat embolism syndrome affecting both lungs". That\'s a central / main? Maybe "main" refers to main pulmonary artery? But it says both lungs, thus bilateral involvement of pulmonary arteries (maybe main? ambiguous). I\'d choose "unknown" because not specific about location segment. But maybe "main" because both lungs suggests main pulmonary arteries (central). The description "multiple fat emboli in the pulmonary arteries" indicates segmental? Not sure. The safe answer likely "unknown" if not clearly indicated as main or segmental.\n\nSide: "bilateral" because both lungs.\n\nThus JSON.\n\n',
    usage: {
      prompt_tokens: 799,
      completion_tokens: 359,
      total_tokens: 1158,
    },
  },
  2425262: {
    result: {
      'shortness of breath': true,
      'chest pain': false,
      'leg pain or swelling': false,
      'heart palpitations': true,
      cough: false,
      dizziness: false,
      location: 'segmental',
      side: 'left',
    },
    reasoning:
      'We need to parse the document. Identify presence of symptoms.\n\nSymptoms listed: "presenting with palpitations and mild dyspnea". Dyspnea = shortness of breath. So shortness of breath: true. chest pain: not mentioned -> false. leg pain or swelling: explicitly "did not exhibit leg swelling" -> false. heart palpitations: true. cough: not mentioned -> false. dizziness: not mentioned -> false.\n\nLocation: They mention "pulmonary embolism in the left lower lobe". That is a segment (lower lobe is a segment? Actually lower lobe comprises multiple segments. Could be considered segmental location. Since they want main / segmental / unknown. Since embolism is in a lobar region not main pulmonary artery, it\'s segmental (lobar is greater than segment but still not main). I\'d select "segmental". side: left (since left lower lobe). So side: left.\n\nReturn JSON.\n\n',
    usage: {
      prompt_tokens: 768,
      completion_tokens: 272,
      total_tokens: 1040,
    },
  },
  3435369: {
    result: {
      'shortness of breath': false,
      'chest pain': false,
      'leg pain or swelling': false,
      'heart palpitations': false,
      cough: false,
      dizziness: false,
      location: 'segmental',
      side: 'right',
    },
    reasoning:
      'We need to extract whether symptoms are mentioned. The report says patient asymptomatic. No mention of shortness of breath, chest pain, leg pain/swelling, palpitations, cough, dizziness. So all false.\n\nLocation refers to embolism location: "right lower lobe of the pulmonary artery". This is a segment? Right lower lobe is a segmental location? Pulmonary embolism location classification: main (central), segmental (lobar?), Actually main = main pulmonary artery; segmental = segmental branches. Right lower lobe is a lobar branch (lobar), not segmental? However they used "segmental" as option. Could also be "unknown". We need to decide best. The embolism is in the right lower lobe of the pulmonary artery, which is more distal than main, perhaps segmental. I\'d pick "segmental". Side: right (since right lower lobe). So side = "right".\n\nReturn JSON with those fields.\n\n',
    usage: {
      prompt_tokens: 773,
      completion_tokens: 276,
      total_tokens: 1049,
    },
  },
  7756987: {
    result: {
      'shortness of breath': true,
      'chest pain': true,
      'leg pain or swelling': true,
      'heart palpitations': false,
      cough: false,
      dizziness: false,
      location: 'segmental',
      side: 'bilateral',
    },
    reasoning:
      'We need to extract whether symptoms are mentioned. Check:\n\n- shortness of breath: present acute shortness of breath. So true.\n- chest pain: pleuritic chest pain present. true.\n- leg pain or swelling: swelling in left lower extremity; mention DVT. So true.\n- heart palpitations: not mentioned. false.\n- cough: not mentioned. false.\n- dizziness: syncope episodes (loss of consciousness). Dizziness not explicitly mentioned. Could infer but it\'s not mentioned. So false.\n- location: refers to pulmonary emboli location. "multiple bilateral segmental pulmonary emboli". So location is segmental. So "segmental".\n- side: "bilateral segmental pulmonary emboli". Also left leg swelling. But for side field likely refer to emboli side; they gave bilateral. So side: "bilateral". The schema allows "left", "right", "bilateral". So set "bilateral".\n\nReturn JSON.',
    usage: {
      prompt_tokens: 790,
      completion_tokens: 274,
      total_tokens: 1064,
    },
  },
  9874562: {
    result: {
      'shortness of breath': true,
      'chest pain': true,
      'leg pain or swelling': true,
      'heart palpitations': true,
      cough: false,
      dizziness: false,
      location: 'main',
      side: 'left',
    },
    reasoning:
      'We need to parse the report for symptoms and location of embolism.\n\nSymptoms:\n\n- "sudden shortness of breath" => shortness of breath true.\n- "chest pain radiating to the shoulder" => chest pain true.\n- "palpitations" => heart palpitations true.\n- "swelling and tenderness in the left calf" => leg pain or swelling true.\n- cough? not mentioned => false.\n- dizziness? not mentioned => false.\n\nLocation: "CTPA demonstrating embolism in the left pulmonary artery." Pulmonary artery is a main artery? The embolism location: left pulmonary artery is a main (central) vessel, not segmental. So location should be "main". side: Left pulmonary artery -> left side. So side = "left".\n\nReturn JSON with booleans.\n\nCheck mapping: use true/false.\n\nThus:\n\n{\n "shortness of breath": true,\n "chest pain": true,\n "leg pain or swelling": true,\n "heart palpitations": true,\n "cough": false,\n "dizziness": false,\n "location": "main",\n "side": "left"\n}\n\nMake sure correct quoting and booleans.\n\n',
    usage: {
      prompt_tokens: 772,
      completion_tokens: 318,
      total_tokens: 1090,
    },
  },
  '0090075': {
    result: {
      'shortness of breath': true,
      'chest pain': true,
      'leg pain or swelling': true,
      'heart palpitations': false,
      cough: true,
      dizziness: false,
      location: 'main',
      side: 'right',
    },
    reasoning:
      'We need to parse report. Determine presence of each symptom.\n\n- shortness of breath: term "dyspnea" which is shortness of breath. Presenting Symptoms: sudden onset dyspnea. So true.\n\n- chest pain: sharp chest pain. Yes, true.\n\n- leg pain or swelling: "mild right calf pain" and DVT. So leg pain present. That counts as leg pain or swelling. true.\n\n- heart palpitations: not mentioned. false.\n\n- cough: presenting symptoms includes coughing up small amounts of blood (hemoptysis). That\'s cough, though with blood. So cough present. true.\n\n- dizziness: not mentioned. false.\n\n- location: refer to embolus location: "large embolus in the right main pulmonary artery". So location is main. So "main". (enum includes main, segmental, unknown). So main.\n\n- side: embolus in right main pulmonary artery → side right. So side "right".\n\nReturn JSON with booleans etc. Ensure correct case: booleans true/false lower case.\n\nThus final JSON.',
    usage: {
      prompt_tokens: 806,
      completion_tokens: 299,
      total_tokens: 1105,
    },
  },
}

const DEFAULT_KEY = '9874562'

function pickDoc(prompt) {
  const m = String(prompt || '').match(/Medical Record Number:\s*0*([0-9]+)/i)
  if (m) {
    // Match on trailing digits so leading zeros in the file id (0090075) resolve.
    const digits = m[1]
    for (const key of Object.keys(DOCS)) {
      if (key.replace(/^0+/, '') === digits) return DOCS[key]
    }
  }
  return DOCS[DEFAULT_KEY]
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
      data: [{ id: 'GPT-OSS-120B', object: 'model', owned_by: 'katherlab' }],
    })
    return
  }

  if (req.method === 'POST' && url.endsWith('/chat/completions')) {
    let raw = ''
    req.on('data', (c) => (raw += c))
    req.on('end', () => {
      let prompt = ''
      try {
        const body = JSON.parse(raw || '{}')
        prompt = (body.messages || []).map((m) => m.content).join('\n')
      } catch {
        // ignore malformed bodies; fall back below
      }
      const doc = pickDoc(prompt)
      const message = {
        role: 'assistant',
        content: JSON.stringify(doc.result),
      }
      // reasoning_content is a non-standard field the backend reads via getattr;
      // the OpenAI SDK exposes it because its models allow extra fields.
      if (doc.reasoning) message.reasoning_content = doc.reasoning
      send(200, {
        id: 'chatcmpl-screenshots',
        object: 'chat.completion',
        model: 'GPT-OSS-120B',
        choices: [{ index: 0, finish_reason: 'stop', message }],
        usage: {
          prompt_tokens: doc.usage.prompt_tokens,
          completion_tokens: doc.usage.completion_tokens,
          total_tokens: doc.usage.total_tokens,
        },
      })
    })
    return
  }

  send(404, { error: 'not found' })
})

server.listen(PORT, HOST, () => {
  console.log(`[screenshots fake-llm] listening on http://${HOST}:${PORT}`)
})
