export type EngagementStatus = 'draft' | 'active' | 'processing' | 'complete' | 'error';

export type FieldType = 'text' | 'currency' | 'date' | 'number';

export interface SchemaField {
  name: string;
  label: string;
  type: FieldType;
}

export interface Engagement {
  id: string;
  client_name: string;
  client_id: string;
  tax_year: number;
  project_name: string;
  status: EngagementStatus;
  confidence_threshold: number;
  output_schema: SchemaField[] | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface EngagementMember {
  engagement_id: string;
  user_id: string;
  role: string;
  added_at: string;
}

export interface OneDriveFolder {
  id: string;
  engagement_id: string;
  folder_path: string;
  display_name: string | null;
  microsoft_user: string | null;
  registered_at: string;
}
