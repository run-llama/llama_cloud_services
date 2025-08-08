type Author = {
  name: string;
  affiliation?: string;
  email?: string;
};

type Methodology = {
  approach?: string;
  participants?: string;
  methods?: string[];
};

type Result = {
  finding?: string;
  significance?: string;
  supportingData?: string;
};

type Reference = {
  title: string;
  authors: string;
  year?: string;
  relevance?: string;
};

type Discussion = {
  implications?: string[];
  limitations?: string[];
  futureWork?: string[];
};

type Publication = {
  journal?: string;
  year: string;
  doi?: string;
  url?: string;
};

export type ResearchData = {
  title: string;
  authors: Author[];
  abstract: string;
  keywords?: string[];
  mainFindings: string[];
  methodology?: Methodology;
  results?: Result[];
  discussion?: Discussion;
  references?: Reference[];
  publication?: Publication;
};

export function renderMarkdown(data: ResearchData): string {
  const {
    title,
    authors,
    abstract,
    keywords,
    mainFindings,
    methodology,
    results,
    discussion,
    references,
    publication,
  } = data;

  const md: string[] = [];

  md.push(`# ${title}\n`);

  // Authors
  md.push(`## Authors`);
  md.push(
    authors
      .map(
        (author) =>
          `- **${author.name}**${
            author.affiliation ? `, *${author.affiliation}*` : ""
          }${author.email ? ` (${author.email})` : ""}`,
      )
      .join("\n"),
  );

  // Abstract
  md.push(`\n## Abstract\n${abstract}`);

  // Keywords
  if (keywords && keywords.length > 0) {
    md.push(`\n## Keywords\n${keywords.map((k) => `- ${k}`).join("\n")}`);
  }

  // Main Findings
  md.push(
    `\n## Main Findings\n${mainFindings.map((f) => `- ${f}`).join("\n")}`,
  );

  // Methodology
  if (methodology) {
    md.push(`\n## Methodology`);
    if (methodology.approach) md.push(`**Approach:** ${methodology.approach}`);
    if (methodology.participants)
      md.push(`**Participants:** ${methodology.participants}`);
    if (methodology.methods?.length) {
      md.push(
        `**Methods:**\n${methodology.methods.map((m) => `- ${m}`).join("\n")}`,
      );
    }
  }

  // Results
  if (results?.length) {
    md.push(`\n## Results`);
    results.forEach((result, i) => {
      md.push(`\n### Result ${i + 1}`);
      if (result.finding) md.push(`- **Finding:** ${result.finding}`);
      if (result.significance)
        md.push(`- **Significance:** ${result.significance}`);
      if (result.supportingData)
        md.push(`- **Supporting Data:** ${result.supportingData}`);
    });
  }

  // Discussion
  if (discussion) {
    md.push(`\n## Discussion`);
    if (discussion.implications?.length) {
      md.push(
        `### Implications\n${discussion.implications
          .map((d) => `- ${d}`)
          .join("\n")}`,
      );
    }
    if (discussion.limitations?.length) {
      md.push(
        `### Limitations\n${discussion.limitations
          .map((d) => `- ${d}`)
          .join("\n")}`,
      );
    }
    if (discussion.futureWork?.length) {
      md.push(
        `### Future Work\n${discussion.futureWork
          .map((d) => `- ${d}`)
          .join("\n")}`,
      );
    }
  }

  // References
  if (references?.length) {
    md.push(`\n## References`);
    references.forEach((ref, i) => {
      md.push(
        `\n**[${i + 1}]** ${ref.title} — *${ref.authors}*${
          ref.year ? ` (${ref.year})` : ""
        }`,
      );
      if (ref.relevance) md.push(`> ${ref.relevance}`);
    });
  }

  // Publication Info
  if (publication) {
    md.push(`\n## Publication`);
    if (publication.journal) md.push(`- **Journal:** ${publication.journal}`);
    if (publication.year) md.push(`- **Year:** ${publication.year}`);
    if (publication.doi) md.push(`- **DOI:** ${publication.doi}`);
    if (publication.url)
      md.push(`- **URL:** [${publication.url}](${publication.url})`);
  }

  return md.join("\n");
}
