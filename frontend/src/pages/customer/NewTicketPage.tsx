import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ErrorMessage } from "../../components/ErrorMessage";
import { useCreateTicket } from "../../hooks/useTickets";
import { ENVIRONMENTS } from "../../types";
import { humanize } from "../../utils/format";

const MIN_SUBJECT = 5;
const MIN_DESCRIPTION = 10;

export function NewTicketPage() {
  const navigate = useNavigate();
  const createTicket = useCreateTicket();
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [environment, setEnvironment] = useState<string>("production");
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (subject.trim().length < MIN_SUBJECT) {
      return setValidationError(`Subject must be at least ${MIN_SUBJECT} characters.`);
    }
    if (description.trim().length < MIN_DESCRIPTION) {
      return setValidationError(`Please describe the problem in at least ${MIN_DESCRIPTION} characters.`);
    }
    setValidationError(null);
    try {
      const ticket = await createTicket.mutateAsync({
        subject: subject.trim(),
        description: description.trim(),
        environment,
      });
      navigate(`/customer/tickets/${ticket.id}`);
    } catch {
      // Displayed via createTicket.error
    }
  };

  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <h1 className="page-title">New support ticket</h1>
        <p className="text-sm text-slate-500">
          Include error messages, timestamps and steps to reproduce so we can help faster.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="card space-y-4 p-6" aria-label="New ticket form">
        {validationError && <ErrorMessage message={validationError} title="Check the form" />}
        {Boolean(createTicket.error) && <ErrorMessage error={createTicket.error} title="Could not create ticket" />}
        <div>
          <label htmlFor="subject" className="label">Subject</label>
          <input
            id="subject"
            className="input"
            maxLength={200}
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. API returns 401 after rotating keys"
          />
        </div>
        <div>
          <label htmlFor="environment" className="label">Environment</label>
          <select
            id="environment"
            className="input"
            value={environment}
            onChange={(e) => setEnvironment(e.target.value)}
          >
            {ENVIRONMENTS.map((env) => (
              <option key={env} value={env}>
                {humanize(env)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="description" className="label">Description</label>
          <textarea
            id="description"
            className="input min-h-[180px]"
            maxLength={10_000}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What happened? What did you expect? Any error codes or logs?"
          />
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={createTicket.isPending}>
            {createTicket.isPending ? "Submitting…" : "Submit ticket"}
          </button>
        </div>
      </form>
    </div>
  );
}
