"use client"

import { useState, useCallback } from "react"
import { FileUpload } from "@/components/file-upload"
import { RequirementsTable, type Requirement } from "@/components/requirements-table"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Monitor, Code, Download, FileSpreadsheet } from "lucide-react"

export default function FileProcessorDashboard() {
  const [file, setFile] = useState<File | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [hardwareRequirements, setHardwareRequirements] = useState<Requirement[]>([])
  const [softwareRequirements, setSoftwareRequirements] = useState<Requirement[]>([])

  const handleFileSelect = useCallback((selectedFile: File | null) => {
    setFile(selectedFile)
    if (!selectedFile) {
      setHardwareRequirements([])
      setSoftwareRequirements([])
    }
  }, [])

  const handleProcessFile = useCallback(async () => {
    if (!file) {
      alert("Upload file first")
      return
    }

    setIsProcessing(true)

    const API_URL =
      process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

    console.log("API URL:", API_URL)

    const formData = new FormData()
    formData.append("file", file)

    try {
      const response = await fetch(`${API_URL}/process`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error("Processing failed")
      }

      const contentType = response.headers.get("content-type") ?? ""

      // FIX: correctly detect non-application responses as errors
      if (!contentType.includes("application")) {
        const text = await response.text()
        console.error("Backend error:", text)
        alert("Backend failed. Check server.")
        return
      }

      const blob = await response.blob()

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "output.xlsx"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

    } catch (err) {
      console.error("ERROR:", err)
      alert("Error processing file")
    } finally {
      setIsProcessing(false)
    }
  }, [file])

  const handleExport = useCallback(() => {
    const headers = ["Category", "Name", "Specification", "Quantity", "Notes"]

    const hardwareRows = hardwareRequirements.map((r) => [
      "Hardware",
      r.name,
      r.specification,
      r.quantity ?? "",   // FIX: null guard to avoid "undefined" in CSV
      r.notes ?? "",      // FIX: null guard to avoid "undefined" in CSV
    ])

    const softwareRows = softwareRequirements.map((r) => [
      "Software",
      r.name,
      r.specification,
      r.quantity ?? "",   // FIX: null guard
      r.notes ?? "",      // FIX: null guard
    ])

    const csvContent = [
      headers.join(","),
      ...hardwareRows.map((row) =>
        row.map((cell) => `"${cell}"`).join(",")
      ),
      ...softwareRows.map((row) =>
        row.map((cell) => `"${cell}"`).join(",")
      ),
    ].join("\n")

    const blob = new Blob([csvContent], { type: "text/csv" })
    const url = URL.createObjectURL(blob)

    const a = document.createElement("a")
    a.href = url
    a.download = "requirements-export.csv"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)

    URL.revokeObjectURL(url)
  }, [hardwareRequirements, softwareRequirements])

  const hasResults =
    hardwareRequirements.length > 0 ||
    softwareRequirements.length > 0

  return (
    <main className="min-h-screen bg-background relative">
      {/* Watermark */}
      <div
        className="fixed inset-0 flex items-center justify-center pointer-events-none select-none z-0"
        aria-hidden="true"
      >
        <div className="flex flex-col items-center text-6xl md:text-8xl lg:text-9xl font-bold text-foreground/[0.04] uppercase tracking-widest leading-tight">
          <span>Acceleron</span>
          <span>Labs</span>
        </div>
      </div>

      {/* Header */}
      <header className="border-b-2 border-border bg-secondary relative z-10">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <FileSpreadsheet className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-2xl font-bold text-secondary-foreground uppercase tracking-wide">
                Requirements Analyzer
              </h1>
              <p className="text-sm text-secondary-foreground/70">
                Upload your specification documents to extract requirements
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8 relative z-10">
        {/* Upload */}
        <section className="mb-8">
          <h2 className="text-lg font-bold mb-4">Step 1: Upload File</h2>
          <FileUpload file={file} onFileSelect={handleFileSelect} />
        </section>

        {/* Process */}
        <section className="mb-8">
          <h2 className="text-lg font-bold mb-4">Step 2: Process File</h2>
          <Button onClick={handleProcessFile} disabled={!file || isProcessing}>
            {isProcessing ? (
              <>
                <Spinner className="mr-2" />
                Processing...
              </>
            ) : (
              "Process File"
            )}
          </Button>
        </section>

        {/* Results */}
        {hasResults && (
          <>
            <RequirementsTable
              title="Hardware Requirements"
              requirements={hardwareRequirements}
              icon={<Monitor className="h-5 w-5 text-primary" />}
            />

            <RequirementsTable
              title="Software Requirements"
              requirements={softwareRequirements}
              icon={<Code className="h-5 w-5 text-primary" />}
            />

            <Button onClick={handleExport} variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          </>
        )}
      </div>
    </main>
  )
}
