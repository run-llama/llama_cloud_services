import { createFileRoute } from '@tanstack/react-router'
import { useRef, useState } from 'react'

export const Route = createFileRoute('/')({
  component: Home,
})

function Home() {
  const [file, setFile] = useState<null | File>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [reply, setReply] = useState<null | string>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
    }
  }
  const handleClearFile = () => {
    if (file) {
      setFile(null)
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    if (reply) {
      setReply(null)
    }
  }

  const handleClassify = async () => {
    if (!file) return

    if (reply) {
      setReply(null)
    }
    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('/api/classify', {
        method: 'POST',
        body: formData,
      })

      const data = await res.json()
      setReply(data.result)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col justify-center items-center gap-y-8">
        <br />
        <h1 className="text-xl font-bold text-gray-700">AI-Powered finacial document classification</h1>
        <h2 className="text-lg font-semibold text-gray-500">Need help sorting out the financial documents jungle? Let our classification agent handle it!</h2>
        <fieldset className="fieldset bg-base-100 border-base-300 rounded-box w-200 border p-4">
            <legend className="fieldset-legend text-lg">Upload your financial document here</legend>
            <label className="label flex justify-center">
                <input type="file" className="file-input" onChange={handleFileChange} accept='application/pdf' ref={fileInputRef} />
            </label>
        </fieldset>
        {file && (
          <div className="flex flex-col justify-center items-center gap-y-8">
          <p className="text-sm text-gray-600">Selected file: {file.name}</p>
          <div className='grid grid-cols-2 gap-x-6'>
            <button
                type="button"
                className='btn bg-gray-500 text-white shadow-lg hover:bg-gray-600 hover:shadow-xl rounded'
                onClick={handleClassify}
            >
            Classify
            </button>
            <button
                  onClick={handleClearFile}
                  type="button"
                  className="px-4 py-2 bg-red-300 text-black rounded hover:bg-red-400 hover:shadow-xl shadow-lg"
              >
              Clear
            </button>
          </div>
          </div>
        )}
        {loading && (
          <span className="loading loading-spinner text-primary"></span>
        )}
        {reply && (
          <div
            className="max-w-2xl w-full"
            dangerouslySetInnerHTML={{ __html: reply }}
          />
        )}
    </div>
  )
}
