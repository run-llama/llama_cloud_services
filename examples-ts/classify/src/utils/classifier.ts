import { LlamaClassify, ClassifierRule, ClassifyParsingConfiguration } from "llama-cloud-services"

export const classifier = new LlamaClassify(process.env.LLAMA_CLOUD_API_KEY);

export const classificationRules: ClassifierRule[] = [
    {
        description: "Shows a company's assets, liabilities, and shareholders' equity at a specific point in time, providing a snapshot of financial position.",
        type: "balance_sheet"
    },
    {
        description: "Reports cash inflows and outflows from operating, investing, and financing activities, highlighting liquidity and cash management.",
        type: "cash_flow_statement"
    },
    {
        description: "Summarizes revenues, expenses, and profits over a period, indicating financial performance and profitability.",
        type: "income_statement"
    },
];

export const parsingConfig: ClassifyParsingConfiguration = {
    lang: "en",
    max_pages: 20,
}
