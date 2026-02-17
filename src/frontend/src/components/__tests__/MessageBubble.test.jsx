import { render, screen } from '@testing-library/react';
import { MessageBubble } from '../MessageBubble.jsx';

describe('MessageBubble', () => {
  it('renders user message styling', () => {
    const message = { id: '1', role: 'user', content: 'User text', status: 'complete' };
    const { container } = render(<MessageBubble message={message} />);

    expect(screen.getByText('User text')).toBeInTheDocument();
    // Updated class check to match new navy design
    const article = container.querySelector('article');
    expect(article).toHaveClass('bg-[#0F172A]');
  });

  it('renders assistant sources when complete', () => {
    const message = {
      id: '2',
      role: 'assistant',
      content: 'Answer',
      status: 'complete',
      sources: [{ name: 'doc-1.md' }],
    };

    render(<MessageBubble message={message} />);

    expect(screen.getByText('Answer')).toBeInTheDocument();
    expect(screen.getByText('doc-1.md')).toBeInTheDocument();
  });
});
