import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders project title', () => {
  render(<App />);
  const titleElement = screen.getByText(/kentsel haber izleme/i);
  expect(titleElement).toBeInTheDocument();
});
