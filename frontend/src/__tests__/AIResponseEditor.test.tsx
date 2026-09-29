import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AIResponseEditor } from "../components/AIResponseEditor";
import { makeAIResponse } from "../test/utils";

function setup(overrides = {}) {
  const handlers = {
    onApprove: vi.fn().mockResolvedValue(undefined),
    onSaveEdit: vi.fn().mockResolvedValue(undefined),
    onReject: vi.fn().mockResolvedValue(undefined),
    onRegenerate: vi.fn().mockResolvedValue(undefined),
  };
  render(<AIResponseEditor response={makeAIResponse(overrides)} {...handlers} />);
  return handlers;
}

describe("AIResponseEditor", () => {
  it("shows the pending draft and states nothing was sent", () => {
    setup();
    expect(screen.getByLabelText("Draft response")).toHaveValue("Please confirm your key starts with ak_live_.");
    expect(screen.getByText(/Nothing has been sent to the customer/)).toBeInTheDocument();
  });

  it("approves an unchanged draft without an edit", async () => {
    const { onApprove } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Approve & send" }));
    expect(onApprove).toHaveBeenCalledWith(undefined);
  });

  it("approves with the edited text when the agent changes the draft", async () => {
    const { onApprove, onSaveEdit } = setup();
    const textarea = screen.getByLabelText("Draft response");
    await userEvent.clear(textarea);
    await userEvent.type(textarea, "Hi Carol, please use a live key.");

    await userEvent.click(screen.getByRole("button", { name: "Save edit" }));
    expect(onSaveEdit).toHaveBeenCalledWith("Hi Carol, please use a live key.");

    await userEvent.click(screen.getByRole("button", { name: "Approve edited & send" }));
    expect(onApprove).toHaveBeenCalledWith("Hi Carol, please use a live key.");
  });

  it("rejects with an optional reason", async () => {
    const { onReject, onApprove } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    await userEvent.type(screen.getByLabelText(/Why is this draft being rejected/), "Wrong product");
    await userEvent.click(screen.getByRole("button", { name: "Confirm reject" }));
    expect(onReject).toHaveBeenCalledWith("Wrong product");
    expect(onApprove).not.toHaveBeenCalled();
  });

  it("can regenerate the draft", async () => {
    const { onRegenerate } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Regenerate" }));
    expect(onRegenerate).toHaveBeenCalled();
  });

  it("is read-only once reviewed", () => {
    setup({ status: "APPROVED", approver: { id: 2, name: "Alice Agent", email: "a@x.dev", role: "AGENT" } });
    expect(screen.queryByLabelText("Draft response")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Approve/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Reviewed by Alice Agent/)).toBeInTheDocument();
  });

  it("lists requested information when the AI needs more details", () => {
    setup({ requires_more_information: true, requested_information: ["HTTP status code", "Timestamp"] });
    expect(screen.getByText("HTTP status code")).toBeInTheDocument();
    expect(screen.getByText("Timestamp")).toBeInTheDocument();
  });
});
