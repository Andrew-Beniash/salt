import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Engagement, EngagementMember, OneDriveFolder, SchemaField } from '@/types/engagement';

// ─── Queries ──────────────────────────────────────────────────────────────────

export function useEngagements() {
  return useQuery<Engagement[]>({
    queryKey: ['engagements'],
    queryFn: async () => {
      const { data } = await api.get<Engagement[]>('/api/engagements');
      return data;
    },
  });
}

export function useEngagement(id: string) {
  return useQuery<Engagement>({
    queryKey: ['engagements', id],
    queryFn: async () => {
      const { data } = await api.get<Engagement>(`/api/engagements/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useEngagementSchema(engagementId: string) {
  return useQuery<{ fields: SchemaField[] }>({
    queryKey: ['engagements', engagementId, 'schema'],
    queryFn: async () => {
      const { data } = await api.get<{ fields: SchemaField[] }>(
        `/api/engagements/${engagementId}/schema`,
      );
      return data;
    },
    enabled: !!engagementId,
  });
}

// ─── Mutations ────────────────────────────────────────────────────────────────

interface CreateEngagementInput {
  client_name: string;
  client_id: string;
  tax_year: number;
  project_name: string;
}

export function useCreateEngagement() {
  const queryClient = useQueryClient();
  return useMutation<Engagement, Error, CreateEngagementInput>({
    mutationFn: async (input) => {
      const { data } = await api.post<Engagement>('/api/engagements', input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['engagements'] });
    },
  });
}

interface AddMemberInput {
  engagementId: string;
  email: string;
  role: string;
}

export function useAddMember() {
  return useMutation<EngagementMember[], Error, AddMemberInput>({
    mutationFn: async ({ engagementId, email, role }) => {
      const { data } = await api.post<EngagementMember[]>(
        `/api/engagements/${engagementId}/members`,
        { email, role },
      );
      return data;
    },
  });
}

interface AddFolderInput {
  engagementId: string;
  folder_path: string;
  display_name?: string;
}

export function useAddFolder() {
  return useMutation<OneDriveFolder[], Error, AddFolderInput>({
    mutationFn: async ({ engagementId, folder_path, display_name }) => {
      const { data } = await api.post<OneDriveFolder[]>(
        `/api/engagements/${engagementId}/folders`,
        { folder_path, display_name: display_name ?? null },
      );
      return data;
    },
  });
}

interface SaveSchemaInput {
  engagementId: string;
  fields: SchemaField[];
}

export function useSaveSchema() {
  const queryClient = useQueryClient();
  return useMutation<{ fields: SchemaField[] }, Error, SaveSchemaInput>({
    mutationFn: async ({ engagementId, fields }) => {
      const { data } = await api.post<{ fields: SchemaField[] }>(
        `/api/engagements/${engagementId}/schema`,
        { fields },
      );
      return data;
    },
    onSuccess: (_, { engagementId }) => {
      queryClient.invalidateQueries({ queryKey: ['engagements', engagementId, 'schema'] });
    },
  });
}
