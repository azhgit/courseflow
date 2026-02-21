import { getExampleQuestions, postQuery } from '../query.js';
import { EXAMPLE_QUESTIONS } from '../../constants/exampleQuestions.js';

describe('query api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('sends query payload to streaming endpoint', async () => {
    const mockResponse = { ok: true };
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(mockResponse);

    await postQuery('What is gravity?', 'conv-123');

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toMatch(/\/api\/v1\/query\/stream$/);
    expect(JSON.parse(options.body)).toEqual({
      query: 'What is gravity?',
      conversation_id: 'conv-123',
    });
  });

  it('returns examples from API', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ examples: ['q1', 'q2'] }),
    });

    const examples = await getExampleQuestions();

    expect(examples).toEqual(['q1', 'q2']);
    expect(fetchSpy).toHaveBeenCalled();
  });

  it('falls back to defaults on 404', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({ ok: false, status: 404 });

    const examples = await getExampleQuestions();

    expect(examples).toEqual(EXAMPLE_QUESTIONS);
  });

  it('falls back to defaults on fetch error', async () => {
    vi.spyOn(global, 'fetch').mockRejectedValue(new Error('network down'));

    const examples = await getExampleQuestions();

    expect(examples).toEqual(EXAMPLE_QUESTIONS);
  });
});
