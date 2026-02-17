import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../../App.jsx';

vi.mock('../../api/query.js', () => ({
  getExampleQuestions: vi.fn().mockResolvedValue(['Example question']),
  postQuery: vi.fn().mockResolvedValue({ body: new ReadableStream({ start: (c) => c.close() }) }),
}));

vi.mock('../../hooks/useStreamingResponse.js', () => ({
  useStreamingResponse: () => ({
    parseSSEStream: vi.fn(async (_r, onChunk, onSources, _onErr, onDone, onConversationId) => {
      onChunk('Demo answer');
      onSources(['demo-source.md']);
      onConversationId('conv-1');
      onDone();
    }),
  }),
}));

describe('chat flow integration', () => {
  it('sends message and renders streamed answer', async () => {
    const user = userEvent.setup();
    render(<App />);

    const input = screen.getByLabelText(/ask a question/i);
    await user.type(input, 'Test question');
    await user.click(screen.getByRole('button', { name: /send/i }));

    expect(await screen.findByText('Test question')).toBeInTheDocument();
    expect(await screen.findByText(/Demo answer/)).toBeInTheDocument();
    expect(await screen.findByText(/demo-source.md/)).toBeInTheDocument();
  });
});
