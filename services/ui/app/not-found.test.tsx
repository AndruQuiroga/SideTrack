import { render, screen } from '@testing-library/react';

import NotFound from './not-found';

describe('NotFound page', () => {
  it('renders a helpful message and link home', () => {
    render(<NotFound />);

    expect(screen.getByRole('heading', { name: /page not found/i })).toBeInTheDocument();

    const homeLink = screen.getByRole('link', { name: /return home/i });
    expect(homeLink).toBeInTheDocument();
    expect(homeLink).toHaveAttribute('href', '/');
  });
});
