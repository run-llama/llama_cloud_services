import { createFileRoute } from '@tanstack/react-router'
import { classifier, classificationRules, parsingConfig } from '~/utils/classifier'

export const Route = createFileRoute('/api/classify')({
  component: RouteComponent,
  server: {
      handlers: {
        POST: async ({ request }) => {
          const body = await request.formData()
          const fl = body.get("file") as File;
          if (!fl) {
                return new Response(JSON.stringify({"result": "you need to provide a file"}))
            }
          const buff = await fl.arrayBuffer()
          const rawRes = await classifier.classify(
            classificationRules,
            parsingConfig,
            { fileContents: [new Uint8Array(buff)] },
          )
          const results = rawRes.items
          let classification = ""

          for (const result of results) {
            if ("result" in result && result.result) {
                classification += `
                    <div class="card bg-base-100 shadow-xl p-6 mb-4">
                        <div class="space-y-3">
                        <p><span class="font-semibold">📄 Document:</span> ${fl.name}</p>
                        <p><span class="font-semibold">🏷️ Type:</span> <span class="badge badge-primary">${result.result.type}</span></p>
                        <p><span class="font-semibold">📊 Confidence:</span> ${result.result.confidence*100}%</p>
                        <p><span class="font-semibold">💭 Reasoning:</span> ${result.result.reasoning}</p>
                        </div>
                    </div>
                `
            }
          }
          return new Response(JSON.stringify({"result": classification}))
        },
      },
    },
})

function RouteComponent() {
  return
}
