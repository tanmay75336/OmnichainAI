const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY || ''
const GEMINI_MODEL =
  import.meta.env.VITE_GEMINI_MODEL || 'gemini-2.0-flash'

function extractTextFromGemini(payload) {
  const parts =
    payload?.candidates?.[0]?.content?.parts?.map((part) => part.text || '') || []
  return parts.join('').trim()
}

function safeParseJson(text) {
  if (!text) {
    return null
  }

  try {
    return JSON.parse(text)
  } catch {
    const fenced = text.match(/```json\s*([\s\S]*?)```/i)?.[1]
    if (!fenced) {
      return null
    }

    try {
      return JSON.parse(fenced)
    } catch {
      return null
    }
  }
}

export function getGeminiConfigState() {
  return GEMINI_API_KEY ? 'configured' : 'missing'
}

export async function fetchGeminiOperationalNews({
  routeData,
  shipmentDate,
  simulationResult,
}) {
  if (!GEMINI_API_KEY) {
    return {
      status: 'not_configured',
      summary:
        'Gemini news intelligence is disabled. Add VITE_GEMINI_API_KEY in frontend/.env to enable route-specific news synthesis.',
      items: [],
    }
  }

  const route = routeData?.route
  const weather = routeData?.weather
  const risk = routeData?.risk
  const simulation = simulationResult
  const cargo = routeData?.cargo_profile
  const traffic = route?.traffic_analysis
  const shipmentPricing = routeData?.shipment_pricing
  const regionContext = routeData?.region_context

  const prompt = [
    'You are generating an Indian logistics decision-intelligence briefing.',
    'Return valid JSON only.',
    'Schema:',
    '{"summary":"string","items":[{"headline":"string","tag":"supply chain|weather|political|holiday","impact":"high|medium|low","detail":"string","recommended_action":"string"}]}',
    'Rules:',
    '- Focus on India-specific logistics exposure.',
    '- Tie the feed to the route, weather, region, and simulation context provided.',
    '- Do not invent company names or fabricated breaking events.',
    '- If live public news is uncertain, provide route-relevant operational watch items rather than fake headlines.',
    '- Keep exactly 4 items.',
    '',
    `Route: ${route?.source_details?.label || route?.source || 'n/a'} -> ${route?.destination_details?.label || route?.destination || 'n/a'}`,
    `Mode: ${route?.transport_mode || 'n/a'}`,
    `Region: ${routeData?.region_type || 'n/a'}`,
    `Region rationale: ${regionContext?.reason || 'n/a'}`,
    `Shipment date: ${shipmentDate || 'not selected'}`,
    `Weather: ${weather?.condition || 'n/a'}, rainfall ${weather?.rainfall_mm ?? 'n/a'} mm, visibility ${weather?.visibility_km ?? 'n/a'} km`,
    `Route outlook: ${(routeData?.weather_outlook || []).map((item) => `${item.date || item.date_index}:${item.condition_label}/${item.avg_temp_c}C`).join(' | ') || 'n/a'}`,
    `Cargo: weight ${cargo?.weight_kg ?? 'n/a'} kg, billable ${cargo?.billable_weight_kg ?? 'n/a'} kg, quantity ${cargo?.quantity ?? 'n/a'}`,
    `Shipment quote: INR ${shipmentPricing?.selected_estimate_inr ?? 'n/a'}, range ${shipmentPricing?.estimated_range_inr?.min ?? 'n/a'}-${shipmentPricing?.estimated_range_inr?.max ?? 'n/a'}`,
    `Traffic: ${traffic?.status || 'n/a'}, delay ${traffic?.projected_delay_minutes ?? 'n/a'} mins, advisory ${traffic?.advisory || 'n/a'}`,
    `Risk: ${risk?.overall_risk || 'n/a'} (${risk?.weighted_score_pct ?? 'n/a'}%)`,
    `Simulation: ${simulation?.summary || 'No active disruption simulation'}`,
  ].join('\n')

  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents: [
          {
            role: 'user',
            parts: [{ text: prompt }],
          },
        ],
        generationConfig: {
          responseMimeType: 'application/json',
          temperature: 0.3,
        },
      }),
    }
  )

  if (!response.ok) {
    throw new Error(`Gemini request failed with status ${response.status}.`)
  }

  const payload = await response.json()
  const text = extractTextFromGemini(payload)
  const parsed = safeParseJson(text)

  if (!parsed) {
    throw new Error('Gemini response could not be parsed as JSON.')
  }

  return {
    status: 'ready',
    summary: parsed.summary || 'Operational intelligence generated.',
    items: Array.isArray(parsed.items) ? parsed.items.slice(0, 4) : [],
  }
}
