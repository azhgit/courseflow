import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInput } from '../ChatInput.jsx';

describe('ChatInput', () => {
  it('submits with button click', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(<ChatInput onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText(/ask a follow-up/i), 'What is AI?');
    await user.click(screen.getByRole('button', { name: /send/i }));

    expect(onSubmit).toHaveBeenCalledWith('What is AI?');
  });

  it('submits with Enter key', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(<ChatInput onSubmit={onSubmit} />);

    const input = screen.getByLabelText(/ask a follow-up/i);
    await user.type(input, 'Hello{enter}');

    expect(onSubmit).toHaveBeenCalledWith('Hello');
  });

  it('does not submit empty input', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(<ChatInput onSubmit={onSubmit} />);
    await user.click(screen.getByRole('button', { name: /send/i }));

    expect(onSubmit).not.toHaveBeenCalled();
  });
});
