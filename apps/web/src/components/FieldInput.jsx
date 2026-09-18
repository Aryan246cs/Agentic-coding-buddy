/**
 * One form field, drawn from its spec.
 *
 * The field's `type` decides the control, so a date field always gets a date
 * picker and a choice field can never be typed into freehand. Used by both the
 * published app's forms and the Test panel, so what a user sees when testing
 * is exactly what their staff will see.
 */

import { Field, Input, Select, Textarea } from './ui';

export default function FieldInput({ field, value, onChange, error, disabled }) {
  const common = {
    id: field.name,
    disabled,
    'aria-invalid': Boolean(error),
    onChange: (event) => onChange(field.name, event.target.value),
  };

  let control;
  switch (field.type) {
    case 'long_text':
      control = <Textarea {...common} value={value ?? ''} rows={3} />;
      break;
    case 'number':
      control = (
        <Input {...common} type="number" step="any" value={value ?? ''} inputMode="decimal" />
      );
      break;
    case 'date':
      control = <Input {...common} type="date" value={value ?? ''} />;
      break;
    case 'boolean':
      control = (
        <Select {...common} value={value === true ? 'true' : value === false ? 'false' : ''}>
          <option value="">Choose…</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </Select>
      );
      break;
    case 'choice':
      control = (
        <Select {...common} value={value ?? ''}>
          <option value="">Choose…</option>
          {field.choices.map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </Select>
      );
      break;
    default:
      control = <Input {...common} type="text" value={value ?? ''} />;
  }

  return (
    <Field
      label={field.label}
      hint={field.help_text}
      error={error}
      required={field.required}
    >
      {control}
    </Field>
  );
}

/** Start values for a form, honouring each field's default. */
export function initialValues(fields) {
  return Object.fromEntries(
    fields.map((field) => [field.name, field.default ?? '']),
  );
}

/** How a stored value should read in a table cell. */
export function displayValue(field, value) {
  if (value === null || value === undefined || value === '') return '—';
  if (field.type === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
}
