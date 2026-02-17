import { render, screen } from '@testing-library/react';
import { ChatHistory } from '../ChatHistory.jsx';

describe('ChatHistory', () => {
  it('renders all messages', () => {
    const messages = [
      { id: '1', role: 'user', content: 'Hi', status: 'complete' },
      { id: '2', role: 'assistant', content: 'Hello', status: 'complete' },
    ];

    render(<ChatHistory messages={messages} isLoading={false} />);

    expect(screen.getByText('Hi')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('shows searching indicator while loading', () => {
    render(<ChatHistory messages={[]} isLoading />);
    expect(screen.getByText(/Searching knowledge base/i)).toBeInTheDocument();
  });
});
