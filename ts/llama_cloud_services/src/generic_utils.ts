export function getContentType(fileName: string): string {
  const ext = fileName.toLowerCase().split(".").pop();
  switch (ext) {
    case "pdf":
      return "application/pdf";
    case "docx":
      return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    case "doc":
      return "application/msword";
    case "txt":
      return "text/plain";
    case "html":
      return "text/html";
    case "md":
      return "text/markdown";
    default:
      return "application/octet-stream";
  }
}
