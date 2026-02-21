import { useId, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  Check,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Plus,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useCreateEngagement,
  useAddMember,
  useAddFolder,
  useSaveSchema,
} from '@/hooks/useEngagements';
import type { FieldType } from '@/types/engagement';

// ─── Local types ──────────────────────────────────────────────────────────────

interface Step1Data {
  client_name: string;
  client_id: string;
  tax_year: string;
  project_name: string;
}

interface MemberDraft {
  _key: string;
  email: string;
  role: 'reviewer' | 'lead';
}

interface FolderDraft {
  folder_path: string;
  display_name: string;
}

interface SchemaFieldDraft {
  _key: string;
  name: string;
  label: string;
  type: FieldType;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STEPS = [
  { n: 1, title: 'Client Details' },
  { n: 2, title: 'Team Members' },
  { n: 3, title: 'OneDrive Folder' },
  { n: 4, title: 'Output Schema' },
] as const;

const FIELD_TYPES: { value: FieldType; label: string }[] = [
  { value: 'text',     label: 'Text' },
  { value: 'currency', label: 'Currency' },
  { value: 'date',     label: 'Date' },
  { value: 'number',   label: 'Number' },
];

const FIELD_NAME_RE = /^[a-zA-Z_][a-zA-Z0-9_]*$/;

// ─── Shared UI helpers ────────────────────────────────────────────────────────

function Label({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="block text-sm font-medium text-gray-700">
      {children}
      {required && <span className="ml-0.5 text-red-500">*</span>}
    </label>
  );
}

function FieldError({ msg }: { msg?: string }) {
  return msg ? <p className="mt-1 text-xs text-red-600">{msg}</p> : null;
}

function TextInput({
  value,
  onChange,
  placeholder,
  hasError,
  type = 'text',
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  hasError?: boolean;
  type?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        'mt-1 w-full rounded-lg border px-3 py-2 text-sm shadow-sm',
        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
        hasError
          ? 'border-red-300 bg-red-50 placeholder-red-300'
          : 'border-gray-300 bg-white placeholder-gray-400',
      )}
    />
  );
}

// ─── Step progress indicator ──────────────────────────────────────────────────

function StepProgress({ current }: { current: number }) {
  return (
    <nav aria-label="Progress" className="mb-8">
      <ol className="flex items-center gap-0">
        {STEPS.map((step, i) => {
          const done = current > step.n;
          const active = current === step.n;
          return (
            <li key={step.n} className="flex items-center">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold',
                    done  && 'bg-green-500 text-white',
                    active && 'bg-blue-600 text-white ring-4 ring-blue-100',
                    !done && !active && 'bg-gray-200 text-gray-500',
                  )}
                >
                  {done ? <Check className="h-4 w-4" /> : step.n}
                </span>
                <span
                  className={cn(
                    'hidden sm:block text-sm',
                    active ? 'font-semibold text-gray-900' : 'text-gray-400',
                  )}
                >
                  {step.title}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className="mx-3 h-px w-8 shrink-0 bg-gray-200 sm:w-14" />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function EngagementCreate() {
  const navigate = useNavigate();
  const uid = useId();

  // wizard step
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  // Step 1
  const [s1, setS1] = useState<Step1Data>({
    client_name: '',
    client_id: '',
    tax_year: String(new Date().getFullYear()),
    project_name: '',
  });
  const [s1Err, setS1Err] = useState<Partial<Record<keyof Step1Data, string>>>({});

  // Step 2
  const [members, setMembers]       = useState<MemberDraft[]>([]);
  const [mEmail, setMEmail]         = useState('');
  const [mRole, setMRole]           = useState<'reviewer' | 'lead'>('reviewer');
  const [mErr, setMErr]             = useState('');

  // Step 3
  const [folder, setFolder] = useState<FolderDraft>({ folder_path: '', display_name: '' });

  // Step 4
  const [schemaFields, setSchemaFields] = useState<SchemaFieldDraft[]>([]);
  const [fName, setFName]   = useState('');
  const [fLabel, setFLabel] = useState('');
  const [fType, setFType]   = useState<FieldType>('text');
  const [fErr, setFErr]     = useState<{ name?: string; label?: string }>({});
  const [schemaErr, setSchemaErr] = useState('');

  // Submit
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitErr, setSubmitErr]       = useState('');

  const createEngagement = useCreateEngagement();
  const addMember        = useAddMember();
  const addFolder        = useAddFolder();
  const saveSchema       = useSaveSchema();

  // ── Step 1 validation ────────────────────────────────────────────────────

  function validateStep1() {
    const e: typeof s1Err = {};
    if (!s1.client_name.trim())  e.client_name  = 'Client name is required.';
    if (!s1.client_id.trim())    e.client_id    = 'Client ID is required.';
    if (!s1.project_name.trim()) e.project_name = 'Project name is required.';
    const yr = parseInt(s1.tax_year, 10);
    if (!s1.tax_year || isNaN(yr) || yr < 2000 || yr > 2100)
      e.tax_year = 'Enter a valid year between 2000 and 2100.';
    setS1Err(e);
    return Object.keys(e).length === 0;
  }

  // ── Step 2 helpers ───────────────────────────────────────────────────────

  function addMemberDraft() {
    setMErr('');
    const email = mEmail.trim().toLowerCase();
    if (!email) { setMErr('Email is required.'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setMErr('Enter a valid email address.');
      return;
    }
    if (members.some((m) => m.email === email)) {
      setMErr('This email has already been added.');
      return;
    }
    setMembers((prev) => [...prev, { _key: `${uid}-${Date.now()}`, email, role: mRole }]);
    setMEmail('');
    setMRole('reviewer');
  }

  // ── Step 4 helpers ───────────────────────────────────────────────────────

  function addFieldDraft() {
    const e: typeof fErr = {};
    const name  = fName.trim();
    const label = fLabel.trim();
    if (!name)                           e.name = 'Field name is required.';
    else if (!FIELD_NAME_RE.test(name))  e.name = 'Letters, digits, underscores only; must start with a letter or _.';
    else if (schemaFields.some((f) => f.name === name)) e.name = 'A field with this name already exists.';
    if (!label) e.label = 'Display label is required.';
    setFErr(e);
    if (Object.keys(e).length > 0) return;

    setSchemaFields((prev) => [
      ...prev,
      { _key: `${uid}-${Date.now()}`, name, label, type: fType },
    ]);
    setFName('');
    setFLabel('');
    setFType('text');
    setSchemaErr('');
  }

  // ── Navigation ───────────────────────────────────────────────────────────

  function goNext() {
    if (step === 1 && !validateStep1()) return;
    setStep((s) => (s + 1) as typeof step);
  }

  function goBack() {
    if (step > 1) setStep((s) => (s - 1) as typeof step);
  }

  // ── Final submit ─────────────────────────────────────────────────────────

  async function handleFinish() {
    if (schemaFields.length === 0) {
      setSchemaErr('Add at least one output field before finishing.');
      return;
    }
    setIsSubmitting(true);
    setSubmitErr('');

    try {
      // 1 — create engagement
      const eng = await createEngagement.mutateAsync({
        client_name:  s1.client_name.trim(),
        client_id:    s1.client_id.trim(),
        tax_year:     parseInt(s1.tax_year, 10),
        project_name: s1.project_name.trim(),
      });

      // 2 — add members in parallel (best-effort; email may not be a known user yet)
      await Promise.allSettled(
        members.map((m) =>
          addMember.mutateAsync({ engagementId: eng.id, email: m.email, role: m.role }),
        ),
      );

      // 3 — add folder if provided (best-effort)
      if (folder.folder_path.trim()) {
        await addFolder
          .mutateAsync({
            engagementId: eng.id,
            folder_path:  folder.folder_path.trim(),
            display_name: folder.display_name.trim() || undefined,
          })
          .catch(() => {/* ignore — can be added from the dashboard */});
      }

      // 4 — save schema (required)
      await saveSchema.mutateAsync({
        engagementId: eng.id,
        fields: schemaFields.map(({ name, label, type }) => ({ name, label, type })),
      });

      navigate(`/engagements/${eng.id}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'An unexpected error occurred.';
      setSubmitErr(msg);
      setIsSubmitting(false);
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">New Engagement</h1>
        <p className="mt-1 text-sm text-gray-500">Set up a new tax engagement in four steps.</p>
      </div>

      <StepProgress current={step} />

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        {step === 1 && <Step1 data={s1} onChange={setS1} errors={s1Err} />}
        {step === 2 && (
          <Step2
            members={members}
            onRemove={(key) => setMembers((p) => p.filter((m) => m._key !== key))}
            email={mEmail}
            onEmailChange={setMEmail}
            role={mRole}
            onRoleChange={setMRole}
            onAdd={addMemberDraft}
            error={mErr}
          />
        )}
        {step === 3 && (
          <Step3
            folder={folder}
            onChange={(k, v) => setFolder((p) => ({ ...p, [k]: v }))}
          />
        )}
        {step === 4 && (
          <Step4
            fields={schemaFields}
            onRemove={(key) => setSchemaFields((p) => p.filter((f) => f._key !== key))}
            name={fName}  onNameChange={setFName}
            label={fLabel} onLabelChange={setFLabel}
            type={fType}  onTypeChange={setFType}
            errors={fErr}
            schemaError={schemaErr}
            onAdd={addFieldDraft}
          />
        )}

        {submitErr && (
          <div className="mt-5 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {submitErr}
          </div>
        )}

        {/* Navigation bar */}
        <div className="mt-8 flex items-center justify-between border-t border-gray-100 pt-6">
          <button
            type="button"
            onClick={goBack}
            disabled={step === 1 || isSubmitting}
            className="inline-flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-4 w-4" /> Back
          </button>

          {step < 4 ? (
            <button
              type="button"
              onClick={goNext}
              className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 transition-colors"
            >
              Next <ChevronRight className="h-4 w-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleFinish}
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-5 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {isSubmitting ? 'Creating…' : 'Create Engagement'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Step 1: Client Details ───────────────────────────────────────────────────

function Step1({
  data,
  onChange,
  errors,
}: {
  data: Step1Data;
  onChange: (d: Step1Data) => void;
  errors: Partial<Record<keyof Step1Data, string>>;
}) {
  const set = (k: keyof Step1Data) => (v: string) => onChange({ ...data, [k]: v });

  return (
    <div className="space-y-5">
      <SectionHeader
        title="Client Details"
        description="Enter the basic information about the client and tax project."
      />

      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <Label required>Client Name</Label>
          <TextInput
            value={data.client_name}
            onChange={set('client_name')}
            placeholder="Acme Corporation"
            hasError={!!errors.client_name}
          />
          <FieldError msg={errors.client_name} />
        </div>

        <div>
          <Label required>Client ID</Label>
          <TextInput
            value={data.client_id}
            onChange={set('client_id')}
            placeholder="ACME-001"
            hasError={!!errors.client_id}
          />
          <FieldError msg={errors.client_id} />
        </div>

        <div>
          <Label required>Tax Year</Label>
          <TextInput
            value={data.tax_year}
            onChange={set('tax_year')}
            placeholder="2024"
            type="number"
            hasError={!!errors.tax_year}
          />
          <FieldError msg={errors.tax_year} />
        </div>

        <div className="col-span-2">
          <Label required>Project Name</Label>
          <TextInput
            value={data.project_name}
            onChange={set('project_name')}
            placeholder="Annual Tax Review 2024"
            hasError={!!errors.project_name}
          />
          <FieldError msg={errors.project_name} />
        </div>
      </div>
    </div>
  );
}

// ─── Step 2: Team Members ─────────────────────────────────────────────────────

function Step2({
  members,
  onRemove,
  email,
  onEmailChange,
  role,
  onRoleChange,
  onAdd,
  error,
}: {
  members: MemberDraft[];
  onRemove: (key: string) => void;
  email: string;
  onEmailChange: (v: string) => void;
  role: 'reviewer' | 'lead';
  onRoleChange: (v: 'reviewer' | 'lead') => void;
  onAdd: () => void;
  error: string;
}) {
  return (
    <div className="space-y-5">
      <SectionHeader
        title="Team Members"
        description="Add colleagues who will work on this engagement. You are automatically added as lead. This step is optional."
      />

      {/* Add row */}
      <div className="flex gap-2 items-end">
        <div className="flex-1">
          <Label>Email Address</Label>
          <input
            type="email"
            value={email}
            onChange={(e) => onEmailChange(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onAdd()}
            placeholder="colleague@firm.com"
            className={cn(
              'mt-1 w-full rounded-lg border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
              error ? 'border-red-300 bg-red-50' : 'border-gray-300 bg-white',
            )}
          />
        </div>
        <div>
          <Label>Role</Label>
          <select
            value={role}
            onChange={(e) => onRoleChange(e.target.value as 'reviewer' | 'lead')}
            className="mt-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="reviewer">Reviewer</option>
            <option value="lead">Lead</option>
          </select>
        </div>
        <button
          type="button"
          onClick={onAdd}
          className="mb-0.5 inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-4 w-4" /> Add
        </button>
      </div>
      {error && <FieldError msg={error} />}

      {/* Member list */}
      {members.length > 0 ? (
        <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200 overflow-hidden">
          {members.map((m) => (
            <li key={m._key} className="flex items-center justify-between px-4 py-2.5 bg-white hover:bg-gray-50">
              <div className="flex items-baseline gap-2">
                <span className="text-sm text-gray-900">{m.email}</span>
                <span className="text-xs capitalize text-gray-400">{m.role}</span>
              </div>
              <button
                type="button"
                onClick={() => onRemove(m._key)}
                className="text-gray-300 hover:text-red-500 transition-colors"
                aria-label={`Remove ${m.email}`}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="py-4 text-center text-sm text-gray-400">No team members added yet.</p>
      )}
    </div>
  );
}

// ─── Step 3: OneDrive Folder ──────────────────────────────────────────────────

function Step3({
  folder,
  onChange,
}: {
  folder: FolderDraft;
  onChange: (key: keyof FolderDraft, value: string) => void;
}) {
  return (
    <div className="space-y-5">
      <SectionHeader
        title="OneDrive Folder"
        description="Connect the OneDrive folder that contains the client's source documents. This step is optional — folders can be added later from the dashboard."
      />

      <div>
        <Label>Folder Path</Label>
        <TextInput
          value={folder.folder_path}
          onChange={(v) => onChange('folder_path', v)}
          placeholder="/Clients/Acme/2024/Tax Documents"
        />
        <p className="mt-1 text-xs text-gray-400">
          Enter the full OneDrive path, e.g. <code>/Clients/Acme Corp/Tax 2024</code>
        </p>
      </div>

      <div>
        <Label>Display Name</Label>
        <TextInput
          value={folder.display_name}
          onChange={(v) => onChange('display_name', v)}
          placeholder="Acme 2024 Tax Docs (optional)"
        />
      </div>

      <div className="flex items-start gap-2 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-700">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        Full OneDrive OAuth integration and an interactive folder picker are available on the
        engagement dashboard after creation.
      </div>
    </div>
  );
}

// ─── Step 4: Output Schema ────────────────────────────────────────────────────

function Step4({
  fields,
  onRemove,
  name,     onNameChange,
  label,    onLabelChange,
  type,     onTypeChange,
  errors,
  schemaError,
  onAdd,
}: {
  fields: SchemaFieldDraft[];
  onRemove: (key: string) => void;
  name: string;     onNameChange: (v: string) => void;
  label: string;    onLabelChange: (v: string) => void;
  type: FieldType;  onTypeChange: (v: FieldType) => void;
  errors: { name?: string; label?: string };
  schemaError: string;
  onAdd: () => void;
}) {
  return (
    <div className="space-y-5">
      <SectionHeader
        title="Output Schema"
        description="Define the fields the AI will extract from each document. Add at least one field to continue."
      />

      {/* Add-field panel */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
          Add a field
        </p>
        <div className="grid grid-cols-2 gap-3">
          {/* name */}
          <div>
            <label className="block text-xs font-medium text-gray-700">
              Field Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => onNameChange(e.target.value)}
              placeholder="sales_tax"
              className={cn(
                'mt-1 w-full rounded-md border px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                errors.name ? 'border-red-300 bg-red-50' : 'border-gray-300 bg-white',
              )}
            />
            <FieldError msg={errors.name} />
          </div>

          {/* label */}
          <div>
            <label className="block text-xs font-medium text-gray-700">
              Display Label <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={label}
              onChange={(e) => onLabelChange(e.target.value)}
              placeholder="Sales Tax"
              className={cn(
                'mt-1 w-full rounded-md border px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                errors.label ? 'border-red-300 bg-red-50' : 'border-gray-300 bg-white',
              )}
            />
            <FieldError msg={errors.label} />
          </div>

          {/* type */}
          <div>
            <label className="block text-xs font-medium text-gray-700">Type</label>
            <select
              value={type}
              onChange={(e) => onTypeChange(e.target.value as FieldType)}
              className="mt-1 w-full rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {FIELD_TYPES.map((ft) => (
                <option key={ft.value} value={ft.value}>{ft.label}</option>
              ))}
            </select>
          </div>

          {/* add button */}
          <div className="flex items-end">
            <button
              type="button"
              onClick={onAdd}
              className="w-full inline-flex items-center justify-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
            >
              <Plus className="h-4 w-4" /> Add Field
            </button>
          </div>
        </div>
      </div>

      {schemaError && (
        <div className="flex items-center gap-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {schemaError}
        </div>
      )}

      {/* Field table */}
      {fields.length > 0 ? (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Name</th>
                <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Label</th>
                <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Type</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {fields.map((f) => (
                <tr key={f._key} className="group hover:bg-gray-50">
                  <td className="px-3 py-2.5 font-mono text-xs text-gray-700">{f.name}</td>
                  <td className="px-3 py-2.5 text-gray-700">{f.label}</td>
                  <td className="px-3 py-2.5">
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium capitalize text-gray-600">
                      {f.type}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <button
                      type="button"
                      onClick={() => onRemove(f._key)}
                      className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all"
                      aria-label={`Remove ${f.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="py-6 text-center text-sm text-gray-400">No fields defined yet.</p>
      )}
    </div>
  );
}

// ─── Section header ───────────────────────────────────────────────────────────

function SectionHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="mb-2">
      <h2 className="text-base font-semibold text-gray-900">{title}</h2>
      <p className="mt-1 text-sm text-gray-500">{description}</p>
    </div>
  );
}
