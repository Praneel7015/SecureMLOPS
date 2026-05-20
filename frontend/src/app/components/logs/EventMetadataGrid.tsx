import { EventField, EventFieldProps } from './EventField';

type EventMetadataGridProps = {
  fields: EventFieldProps[];
};

export function EventMetadataGrid({ fields }: EventMetadataGridProps) {
  if (fields.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No structured details available for this event.</p>
    );
  }

  const metrics = fields.filter((field) => field.variant === 'metric');
  const regular = fields.filter((field) => field.variant !== 'metric');

  return (
    <div className="space-y-4">
      {metrics.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {metrics.map((field) => (
            <EventField key={field.label} {...field} />
          ))}
        </div>
      )}

      {regular.length > 0 && (
        <div className="grid grid-cols-1 gap-4 border-t border-border/50 pt-4 sm:grid-cols-2 lg:grid-cols-3">
          {regular.map((field) => (
            <EventField key={field.label} {...field} />
          ))}
        </div>
      )}
    </div>
  );
}
