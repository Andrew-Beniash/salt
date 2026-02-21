/**
 * SchemaBuilder — drag-and-drop output field builder (FR-014).
 *
 * Renders:
 *  1. Template picker  — one-click starting schema for Invoice / Receipt / Exemption Certificate
 *  2. Add-field form   — name (machine key), display label, type dropdown
 *  3. Sortable list    — drag handle, field info, per-row delete
 *  4. Live preview     — vertical table showing current field order and sample values
 *  5. Save button      — POST to /engagements/{id}/schema
 *
 * Props:
 *  engagementId — UUID of the parent engagement
 *  locked       — when true (status = processing | complete) all mutation controls are hidden
 */

import { useEffect, useId, useState } from 'react';
import {
  DndContext,
  DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  AlertCircle,
  CheckCircle2,
  GripVertical,
  Loader2,
  Plus,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useEngagementSchema, useSaveSchema } from '@/hooks/useEngagements';
import type { FieldType } from '@/types/engagement';

// ─── Types ────────────────────────────────────────────────────────────────────

interface FieldDraft {
  /** Stable local ID used as the DnD sort key — never sent to the API. */
  id: string;
  name: string;
  label: string;
  type: FieldType;
}

// ─── Templates ────────────────────────────────────────────────────────────────

interface Template {
  id: string;
  title: string;
  icon: string;
  description: string;
  fields: Omit<FieldDraft, 'id'>[];
}

const TEMPLATES: Template[] = [
  {
    id: 'invoice',
    title: 'Invoice',
    icon: '🧾',
    description: 'Vendor invoice with amounts and payment terms.',
    fields: [
      { name: 'vendor_name',    label: 'Vendor Name',    type: 'text'     },
      { name: 'invoice_number', label: 'Invoice Number', type: 'text'     },
      { name: 'invoice_date',   label: 'Invoice Date',   type: 'date'     },
      { name: 'due_date',       label: 'Due Date',       type: 'date'     },
      { name: 'subtotal',       label: 'Subtotal',       type: 'currency' },
      { name: 'tax_amount',     label: 'Tax Amount',     type: 'currency' },
      { name: 'total_amount',   label: 'Total Amount',   type: 'currency' },
    ],
  },
  {
    id: 'receipt',
    title: 'Receipt',
    icon: '🏷️',
    description: 'POS or vendor receipt with line totals.',
    fields: [
      { name: 'merchant_name',   label: 'Merchant Name',   type: 'text'     },
      { name: 'receipt_date',    label: 'Receipt Date',    type: 'date'     },
      { name: 'subtotal',        label: 'Subtotal',        type: 'currency' },
      { name: 'tax',             label: 'Tax',             type: 'currency' },
      { name: 'total',           label: 'Total',           type: 'currency' },
      { name: 'payment_method',  label: 'Payment Method',  type: 'text'     },
    ],
  },
  {
    id: 'exemption',
    title: 'Exemption Certificate',
    icon: '📋',
    description: 'Tax exemption certificate with validity period.',
    fields: [
      { name: 'entity_name',         label: 'Entity Name',        type: 'text' },
      { name: 'certificate_number',  label: 'Certificate No.',    type: 'text' },
      { name: 'exemption_type',      label: 'Exemption Type',     type: 'text' },
      { name: 'state',               label: 'State',              type: 'text' },
      { name: 'issue_date',          label: 'Issue Date',         type: 'date' },
      { name: 'expiry_date',         label: 'Expiry Date',        type: 'date' },
    ],
  },
];

// ─── Constants ────────────────────────────────────────────────────────────────

const FIELD_TYPES: { value: FieldType; label: string }[] = [
  { value: 'text',     label: 'Text'     },
  { value: 'currency', label: 'Currency' },
  { value: 'date',     label: 'Date'     },
  { value: 'number',   label: 'Number'   },
];

const PREVIEW_SAMPLES: Record<FieldType, string> = {
  text:     'Sample text',
  currency: '$1,234.56',
  date:     '2024-01-15',
  number:   '42',
};

const TYPE_CHIP_COLOUR: Record<FieldType, string> = {
  text:     'bg-gray-100 text-gray-600',
  currency: 'bg-green-50 text-green-700',
  date:     'bg-purple-50 text-purple-700',
  number:   'bg-blue-50 text-blue-700',
};

const FIELD_NAME_RE = /^[a-zA-Z_][a-zA-Z0-9_]*$/;

function newId() {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

// ─── SortableFieldRow ─────────────────────────────────────────────────────────

function SortableFieldRow({
  field,
  onRemove,
  disabled,
}: {
  field: FieldDraft;
  onRemove: (id: string) => void;
  disabled?: boolean;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: field.id, disabled });

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        'group flex items-center gap-3 rounded-lg border bg-white px-3 py-2.5 select-none',
        isDragging
          ? 'border-blue-400 opacity-60 shadow-lg ring-2 ring-blue-300'
          : 'border-gray-200',
      )}
    >
      {/* Drag handle */}
      <button
        type="button"
        {...listeners}
        {...attributes}
        disabled={disabled}
        aria-label="Drag to reorder"
        className={cn(
          'shrink-0 touch-none text-gray-300 transition-colors',
          disabled
            ? 'cursor-default opacity-30'
            : 'cursor-grab hover:text-gray-500 active:cursor-grabbing',
        )}
      >
        <GripVertical className="h-4 w-4" />
      </button>

      {/* Machine key */}
      <code className="w-40 shrink-0 truncate font-mono text-xs text-gray-600">
        {field.name}
      </code>

      {/* Display label */}
      <span className="flex-1 truncate text-sm text-gray-800">{field.label}</span>

      {/* Type chip */}
      <span
        className={cn(
          'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium capitalize',
          TYPE_CHIP_COLOUR[field.type],
        )}
      >
        {field.type}
      </span>

      {/* Delete */}
      <button
        type="button"
        onClick={() => onRemove(field.id)}
        disabled={disabled}
        aria-label={`Remove ${field.name}`}
        className="ml-1 shrink-0 text-gray-300 opacity-0 transition-all hover:text-red-500 group-hover:opacity-100 disabled:pointer-events-none disabled:opacity-0"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}

// ─── SchemaBuilder ────────────────────────────────────────────────────────────

interface SchemaBuilderProps {
  engagementId: string;
  /** True when engagement.status is processing or complete. Hides all edit controls. */
  locked?: boolean;
}

export function SchemaBuilder({ engagementId, locked = false }: SchemaBuilderProps) {
  const uid = useId();

  const { data: schemaData, isLoading } = useEngagementSchema(engagementId);
  const saveSchema = useSaveSchema();

  // ── Fields state ────────────────────────────────────────────────────────
  const [fields, setFields]         = useState<FieldDraft[]>([]);
  const [initialized, setInitialized] = useState(false);

  // Seed from API exactly once — don't overwrite in-progress edits on refetch
  useEffect(() => {
    if (!initialized && schemaData !== undefined) {
      setFields(
        (schemaData.fields ?? []).map((f) => ({ id: newId(), ...f })),
      );
      setInitialized(true);
    }
  }, [schemaData, initialized]);

  // ── Add-field form ──────────────────────────────────────────────────────
  const [fName,  setFName]  = useState('');
  const [fLabel, setFLabel] = useState('');
  const [fType,  setFType]  = useState<FieldType>('text');
  const [fErr,   setFErr]   = useState<{ name?: string; label?: string }>({});

  // ── Save feedback ───────────────────────────────────────────────────────
  const [saveErr,     setSaveErr]     = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);

  // ── DnD setup ───────────────────────────────────────────────────────────
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragEnd({ active, over }: DragEndEvent) {
    if (!over || active.id === over.id) return;
    setFields((items) => {
      const from = items.findIndex((i) => i.id === active.id);
      const to   = items.findIndex((i) => i.id === over.id);
      return arrayMove(items, from, to);
    });
    setSaveSuccess(false);
  }

  // ── Field helpers ───────────────────────────────────────────────────────
  function addField() {
    const e: typeof fErr = {};
    const name  = fName.trim();
    const label = fLabel.trim();

    if (!name)                                    e.name = 'Field name is required.';
    else if (!FIELD_NAME_RE.test(name))           e.name = 'Letters, digits, and underscores only; must start with a letter or _.';
    else if (fields.some((f) => f.name === name)) e.name = 'A field with this name already exists.';
    if (!label)                                   e.label = 'Display label is required.';

    setFErr(e);
    if (Object.keys(e).length > 0) return;

    setFields((prev) => [...prev, { id: `${uid}${Date.now()}`, name, label, type: fType }]);
    setFName('');
    setFLabel('');
    setFType('text');
    setSaveSuccess(false);
  }

  function removeField(id: string) {
    setFields((prev) => prev.filter((f) => f.id !== id));
    setSaveSuccess(false);
  }

  // ── Template helpers ────────────────────────────────────────────────────
  function applyTemplate(tpl: Template) {
    if (
      fields.length > 0 &&
      !window.confirm(
        `Replace the current ${fields.length} field(s) with the "${tpl.title}" template?`,
      )
    ) {
      return;
    }
    setFields(tpl.fields.map((f) => ({ id: newId(), ...f })));
    setSaveSuccess(false);
    setFErr({});
  }

  // ── Save ────────────────────────────────────────────────────────────────
  async function handleSave() {
    setSaveErr('');
    setSaveSuccess(false);

    if (fields.length === 0) {
      setSaveErr('Add at least one field before saving the schema.');
      return;
    }

    try {
      await saveSchema.mutateAsync({
        engagementId,
        fields: fields.map(({ name, label, type }) => ({ name, label, type })),
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err) {
      setSaveErr(err instanceof Error ? err.message : 'Failed to save schema.');
    }
  }

  // ── Loading skeleton ────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-10 text-gray-400">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="text-sm">Loading schema…</span>
      </div>
    );
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Output Schema</h2>
          <p className="mt-0.5 text-sm text-gray-500">
            {locked
              ? 'Schema is locked while the engagement is processing or complete.'
              : 'Define the fields the AI will extract. Drag rows to reorder.'}
          </p>
        </div>

        {!locked && (
          <button
            type="button"
            onClick={handleSave}
            disabled={saveSchema.isPending}
            className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
          >
            {saveSchema.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            {saveSchema.isPending ? 'Saving…' : 'Save Schema'}
          </button>
        )}
      </div>

      {/* ── Status banners ──────────────────────────────────────────────── */}
      {saveSuccess && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Schema saved successfully.
        </div>
      )}
      {saveErr && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {saveErr}
        </div>
      )}

      {/* ── Template picker ─────────────────────────────────────────────── */}
      {!locked && (
        <section>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
            Start from a template
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {TEMPLATES.map((tpl) => (
              <button
                key={tpl.id}
                type="button"
                onClick={() => applyTemplate(tpl)}
                className="group flex flex-col items-start gap-1 rounded-lg border border-gray-200 bg-white p-4 text-left shadow-sm transition-colors hover:border-blue-400 hover:bg-blue-50"
              >
                <span className="text-2xl" aria-hidden="true">{tpl.icon}</span>
                <span className="text-sm font-semibold text-gray-900 group-hover:text-blue-700">
                  {tpl.title}
                </span>
                <span className="text-xs text-gray-500">{tpl.description}</span>
                <span className="mt-1 text-xs font-medium text-blue-600">
                  {tpl.fields.length} fields →
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* ── Builder + Preview two-column layout ─────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_280px]">

        {/* LEFT — add-field form + sortable list ──────────────────────── */}
        <div className="space-y-3">
          {!locked && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
                Add a field
              </p>
              <div className="grid grid-cols-2 gap-3">

                {/* name */}
                <div>
                  <label className="block text-xs font-medium text-gray-700">
                    Field name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={fName}
                    onChange={(e) => {
                      setFName(e.target.value);
                      setFErr((p) => ({ ...p, name: undefined }));
                    }}
                    onKeyDown={(e) => e.key === 'Enter' && addField()}
                    placeholder="sales_tax"
                    className={cn(
                      'mt-1 w-full rounded-md border px-2.5 py-1.5 text-sm',
                      'focus:outline-none focus:ring-2 focus:ring-blue-500',
                      fErr.name
                        ? 'border-red-300 bg-red-50'
                        : 'border-gray-300 bg-white',
                    )}
                  />
                  {fErr.name && (
                    <p className="mt-0.5 text-xs text-red-600">{fErr.name}</p>
                  )}
                </div>

                {/* label */}
                <div>
                  <label className="block text-xs font-medium text-gray-700">
                    Display label <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={fLabel}
                    onChange={(e) => {
                      setFLabel(e.target.value);
                      setFErr((p) => ({ ...p, label: undefined }));
                    }}
                    onKeyDown={(e) => e.key === 'Enter' && addField()}
                    placeholder="Sales Tax"
                    className={cn(
                      'mt-1 w-full rounded-md border px-2.5 py-1.5 text-sm',
                      'focus:outline-none focus:ring-2 focus:ring-blue-500',
                      fErr.label
                        ? 'border-red-300 bg-red-50'
                        : 'border-gray-300 bg-white',
                    )}
                  />
                  {fErr.label && (
                    <p className="mt-0.5 text-xs text-red-600">{fErr.label}</p>
                  )}
                </div>

                {/* type */}
                <div>
                  <label className="block text-xs font-medium text-gray-700">Type</label>
                  <select
                    value={fType}
                    onChange={(e) => setFType(e.target.value as FieldType)}
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
                    onClick={addField}
                    className="w-full inline-flex items-center justify-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                    Add Field
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Sortable list */}
          {fields.length > 0 ? (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={fields.map((f) => f.id)}
                strategy={verticalListSortingStrategy}
              >
                <div className="space-y-2">
                  {fields.map((f) => (
                    <SortableFieldRow
                      key={f.id}
                      field={f}
                      onRemove={removeField}
                      disabled={locked}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          ) : (
            <div className="rounded-lg border-2 border-dashed border-gray-200 py-12 text-center">
              <p className="text-sm text-gray-400">
                {locked
                  ? 'No schema has been defined for this engagement.'
                  : 'Add a field above or choose a template to get started.'}
              </p>
            </div>
          )}
        </div>

        {/* RIGHT — live preview ────────────────────────────────────────── */}
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
            Live preview
          </p>

          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
            {fields.length > 0 ? (
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50">
                    <th className="w-6 px-2 py-2 text-center text-[10px] font-semibold text-gray-400">#</th>
                    <th className="px-3 py-2 text-left font-semibold text-gray-600">Label</th>
                    <th className="px-3 py-2 text-right font-semibold text-gray-400">Sample</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {fields.map((f, i) => (
                    <tr key={f.id} className="hover:bg-gray-50/60">
                      <td className="px-2 py-2 text-center text-[10px] text-gray-300">
                        {i + 1}
                      </td>
                      <td className="px-3 py-2">
                        <span className="block font-medium text-gray-700">{f.label}</span>
                        <code className="text-[10px] text-gray-400">{f.name}</code>
                      </td>
                      <td className="px-3 py-2 text-right text-gray-300 italic">
                        {PREVIEW_SAMPLES[f.type]}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="px-4 py-8 text-center text-xs text-gray-400">
                No fields yet.
              </p>
            )}
          </div>

          {fields.length > 0 && (
            <p className="text-[11px] text-gray-400">
              {fields.length} field{fields.length !== 1 ? 's' : ''}
              {!locked && ' · drag rows to reorder'}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
