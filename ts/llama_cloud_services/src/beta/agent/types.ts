import type { FilterOperation as RawFilterOperation } from "../../client/types.gen";
/**
 * Status types for agent data processing
 */
export const StatusType = {
  ERROR: "error",
  ACCEPTED: "accepted",
  REJECTED: "rejected",
  PENDING_REVIEW: "pending_review",
} as const;

export type StatusType = (typeof StatusType)[keyof typeof StatusType];

export const ComparisonOperator = {
  GT: "gt",
  GTE: "gte",
  LT: "lt",
  LTE: "lte",
  EQ: "eq",
  INCLUDES: "includes",
} as const;

export type ComparisonOperator =
  (typeof ComparisonOperator)[keyof typeof ComparisonOperator];

/**
 * Filter operation for searching/filtering agent data
 */
export type FilterOperation = RawFilterOperation;

/**
 * Metadata for an extracted field, including confidence and citation information
 */
export interface ExtractedFieldMetadata {
  /** The confidence score for the field, combined with parsing confidence if applicable */
  confidence?: number;
  /** The confidence score for the field based on the extracted text only */
  extracted_confidence?: number;
  /** The page number that the field occurred on */
  page_number?: number;
  /** The original text this field's value was derived from */
  matching_text?: string;
}

/**
 * Dictionary mapping field names to their metadata
 * Values can be ExtractedFieldMetadata objects, nested dictionaries, or arrays
 */
export type ExtractedFieldMetadataDict = Record<
  string,
  ExtractedFieldMetadata | Record<string, unknown> | unknown[]
>;

/**
 * Base extracted data interface
 */
export interface ExtractedData<T = unknown> {
  /** The original data that was extracted from the document. For tracking changes. Should not be updated. */
  original_data: T;
  /** The latest state of the data. Will differ if data has been updated. */
  data: T;
  /** The status of the extracted data. Prefer to use the StatusType values, but any string is allowed. */
  status: StatusType | string;
  /** The overall confidence score for the extracted data. */
  overall_confidence?: number;
  /** Page links, and perhaps eventually bounding boxes, for individual fields in the extracted data. */
  field_metadata?: ExtractedFieldMetadataDict;
  /** The ID of the file that was used to extract the data. */
  file_id?: string;
  /** The name of the file that was used to extract the data. */
  file_name?: string;
  /** The hash of the file that was used to extract the data. */
  file_hash?: string;
  /** Additional metadata about the extracted data, such as errors, tokens, etc. */
  metadata?: Record<string, unknown>;
}

/**
 * TypedAgentData interface for typed agent data
 */
export interface TypedAgentData<T = unknown> {
  /** The unique ID of the agent data record. */
  id: string;
  /** The ID of the agent that created the data. */
  agentUrlId: string;
  /** The collection of the agent data. */
  collection?: string;
  /** The data of the agent data. Usually an ExtractedData&lt;SomeOtherType&gt; */
  data: T;
  /** The date and time the data was created. */
  createdAt: Date;
  /** The date and time the data was last updated. */
  updatedAt: Date;
}

/**
 * Paginated response of typed agent data items
 */
export interface TypedAgentDataItems<T = unknown> {
  items: TypedAgentData<T>[];
  totalSize?: number;
  nextPageToken?: string;
}

/**
 * Options for listing agent data
 */
export interface SearchAgentDataOptions {
  /** Filter options for the list. */
  filter?: Record<string, FilterOperation>;
  /** Order by options for the list. */
  orderBy?: string;
  /** Page size for the list. */
  pageSize?: number;
  /** Offset for the list. */
  offset?: number;
  /**
   * Whether to include the total number of items in the response.
   * Should use only for first request to build total pagination, and not subsequent requests.
   */
  includeTotal?: boolean;
}

/**
 * Options for aggregating agent data
 */
export interface AggregateAgentDataOptions {
  /** Filter options for the aggregation. */
  filter?: Record<string, FilterOperation>;
  /** Fields to group by. */
  groupBy?: string[];
  /** Whether to count the number of items in each group. */
  count?: boolean;
  /** Whether to return the first item in each group. */
  first?: boolean;
  /** Order by options for the aggregation. */
  orderBy?: string;
  /** Offset for the aggregation. */
  offset?: number;
  /** Page size for the aggregation. */
  pageSize?: number;
}

/**
 * Single aggregation group result
 */
export interface TypedAggregateGroup<T = unknown> {
  /** The group key values */
  groupKey: Record<string, unknown>;
  /** Count of items in the group */
  count?: number;
  /** First item in the group */
  firstItem?: T;
}

/**
 * Paginated response of aggregated agent data
 */
export interface TypedAggregateGroupItems<T = unknown> {
  items: TypedAggregateGroup<T>[];
  totalSize?: number;
  nextPageToken?: string;
}
