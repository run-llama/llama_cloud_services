import fs from "fs/promises";
import { Blob } from "buffer";
import * as path from "path";
import { randomUUID } from "@llamaindex/env";
import { File } from "buffer";
import {
  type Options,
  type UploadFileApiV1FilesPostData,
  uploadFileApiV1FilesPost,
} from "./api";
import type { Client } from "@hey-api/client-fetch";
import { sleep } from "./utils";
import { fileTypeFromBuffer } from "file-type";

type BodyUploadFileApiV1FilesPost = {
  upload_file: Blob | File;
};

function textToFile(text: string, fileName: string | null = null) {
  return new File(
    [text],
    fileName ?? "uploadedFile_" + randomUUID().replaceAll("-", "_") + ".txt",
  );
}

export async function uploadFile({
  filePath,
  fileContent,
  fileName,
  project_id,
  organization_id,
  client,
  maxRetriesOnError = 10,
  retryInterval = 0.5,
}: {
  filePath?: string | undefined;
  fileContent?:
    | Buffer<ArrayBufferLike>
    | File
    | Uint8Array<ArrayBuffer>
    | string
    | undefined;
  fileName?: string | undefined;
  project_id?: string | undefined;
  organization_id?: string | undefined;
  client?: Client | undefined;
  maxRetriesOnError?: number;
  retryInterval?: number;
}): Promise<string | undefined> {
  let file: File | undefined = undefined;
  if (typeof filePath === "undefined" && typeof fileContent === "undefined") {
    throw new Error(
      "One between filePath and fileContent needs to be provided",
    );
  } else if (typeof filePath != "undefined") {
    const buffer = await fs.readFile(filePath);
    const actualFileName = fileName ?? path.basename(filePath);
    const uint8Array = new Uint8Array(buffer);
    file = new File([uint8Array], actualFileName);
  } else if (typeof fileContent != "undefined") {
    if (fileContent instanceof File) {
      file = fileContent;
    } else if (fileContent instanceof Buffer) {
      const fileType = await fileTypeFromBuffer(fileContent);
      const ext = fileType?.ext ?? "pdf";
      const uint8Array = new Uint8Array(fileContent);
      file = new File(
        [uint8Array],
        fileName ??
          "uploadedFile_" + randomUUID().replaceAll("-", "_") + "." + ext,
      );
    } else if (fileContent instanceof Uint8Array) {
      const fileType = await fileTypeFromBuffer(fileContent);
      const ext = fileType?.ext ?? "pdf";
      file = new File(
        [fileContent],
        fileName ??
          "uploadedFile_" + randomUUID().replaceAll("-", "_") + "." + ext,
      );
    } else if (typeof fileContent === "string") {
      file = textToFile(fileContent, fileName);
    } else {
      throw new Error("Unsupported fileContent type");
    }
  }
  const fileToUpload = {
    upload_file: file,
  } as BodyUploadFileApiV1FilesPost;
  const uploadData = {
    body: fileToUpload,
    query: { project_id: project_id, organization_id: organization_id },
  } as UploadFileApiV1FilesPostData;
  const uploadOptions = uploadData as Options<UploadFileApiV1FilesPostData>;
  if (typeof client != "undefined") {
    uploadOptions.client = client;
  }
  let retries: number = 0;
  while (true) {
    if (retries > maxRetriesOnError) {
      throw new Error(
        "Error while processing your file: Exceeded maximum number of retries, the API keeps returning errors.",
      );
    }
    const uploadResponse = await uploadFileApiV1FilesPost(uploadOptions);
    let fileId: string | undefined = undefined;
    if (!uploadResponse.response.ok) {
      const error = await uploadResponse.response.text();
      console.error("Error while uploading file: ", error);
      retries++;
      await sleep(retryInterval * 1000);
    }
    if (
      uploadResponse.response.ok &&
      typeof uploadResponse.data != "undefined"
    ) {
      fileId = uploadResponse.data.id as string;
      return fileId;
    }
  }
}
