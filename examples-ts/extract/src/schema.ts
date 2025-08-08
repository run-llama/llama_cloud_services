export const dataSchema = {
  type: "object",
  required: ["title", "authors", "abstract", "mainFindings"],
  properties: {
    title: {
      type: "string",
      description: "The full title of the research paper",
    },
    authors: {
      type: "array",
      description: "List of all authors of the paper",
      items: {
        type: "object",
        properties: {
          name: {
            type: "string",
            description: "Full name of the author",
          },
          affiliation: {
            type: "string",
            description:
              "Institution or organization the author is affiliated with",
          },
          email: {
            type: "string",
            description: "Contact email of the author if provided",
          },
        },
      },
    },
    abstract: {
      type: "string",
      description: "Complete abstract or summary of the paper",
    },
    keywords: {
      type: "array",
      description:
        "Key terms and phrases that describe the paper's main topics",
      items: {
        type: "string",
      },
    },
    mainFindings: {
      type: "array",
      description: "Key findings, conclusions, or contributions of the paper",
      items: {
        type: "string",
      },
    },
    methodology: {
      type: "object",
      description: "Research methods and approaches used",
      properties: {
        approach: {
          type: "string",
          description: "Overall research approach or study design",
        },
        participants: {
          type: "string",
          description: "Description of study participants or data sources",
        },
        methods: {
          type: "array",
          description: "Specific methods, techniques, or tools used",
          items: {
            type: "string",
          },
        },
      },
    },
    results: {
      type: "array",
      description: "Main results and outcomes of the research",
      items: {
        type: "object",
        properties: {
          finding: {
            type: "string",
            description: "Description of the specific result or finding",
          },
          significance: {
            type: "string",
            description:
              "Statistical significance or importance of the finding",
          },
          supportingData: {
            type: "string",
            description: "Relevant statistics, measurements, or data points",
          },
        },
      },
    },
    discussion: {
      type: "object",
      properties: {
        implications: {
          type: "array",
          description: "Theoretical or practical implications of the findings",
          items: {
            type: "string",
          },
        },
        limitations: {
          type: "array",
          description: "Study limitations or constraints",
          items: {
            type: "string",
          },
        },
        futureWork: {
          type: "array",
          description: "Suggested future research directions",
          items: {
            type: "string",
          },
        },
      },
    },
    references: {
      type: "array",
      description:
        "Key papers cited that are crucial to understanding this work",
      items: {
        type: "object",
        properties: {
          title: {
            type: "string",
            description: "Title of the cited paper",
          },
          authors: {
            type: "string",
            description: "Authors of the cited paper",
          },
          year: {
            type: "string",
            description: "Publication year",
          },
          relevance: {
            type: "string",
            description: "Why this reference is important to the current paper",
          },
        },
        required: ["title", "authors"],
      },
    },
    publication: {
      type: "object",
      properties: {
        journal: {
          type: "string",
          description: "Name of the journal or conference",
        },
        year: {
          type: "string",
          description: "Year of publication",
        },
        doi: {
          type: "string",
          description: "Digital Object Identifier (DOI) of the paper",
        },
        url: {
          type: "string",
          description: "URL where the paper can be accessed",
        },
      },
      required: ["year"],
    },
  },
};
