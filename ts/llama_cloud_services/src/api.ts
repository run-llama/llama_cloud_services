import { client } from "./client/client.gen";

client.setConfig({
  baseUrl: "https://api.cloud.llamaindex.ai/",
  headers: {
    "X-SDK-Name": "llamaindex-ts",
  },
});

export * from "./client";
export { client };
