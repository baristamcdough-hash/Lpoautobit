import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Dashboard from '../pages/Dashboard';

vi.mock('../services/api', () => ({
  getDashboard: vi.fn(),
  toggleItemStatus: vi.fn(),
}));

import { getDashboard } from '../services/api';

const mockGetDashboard = vi.mocked(getDashboard);

function renderDashboard() {
  return render(
    <BrowserRouter>
      <Dashboard />
    </BrowserRouter>
  );
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders date picker', async () => {
    mockGetDashboard.mockResolvedValue({
      date: '2024-01-15',
      master_procurement: [],
      distribution: [],
    });

    renderDashboard();

    await waitFor(() => {
      const datePicker = screen.getByDisplayValue(
        new Date().toISOString().split('T')[0]
      );
      expect(datePicker).toBeInTheDocument();
    });
  });

  it('renders "Master Procurement Total" heading when data is loaded', async () => {
    mockGetDashboard.mockResolvedValue({
      date: '2024-01-15',
      master_procurement: [
        { item_name: 'Tomatoes', total_quantity: 100, unit: 'kg', item_ids: [1], item_statuses: ['pending'] },
      ],
      distribution: [
        {
          customer_name: 'Safari Hotel',
          items: [{ item_name: 'Tomatoes', quantity: 50, unit: 'kg' }],
        },
      ],
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Master Procurement Total')).toBeInTheDocument();
    });
  });

  it('renders distribution breakdown with customer names', async () => {
    mockGetDashboard.mockResolvedValue({
      date: '2024-01-15',
      master_procurement: [
        { item_name: 'Potatoes', total_quantity: 200, unit: 'kg', item_ids: [2, 3], item_statuses: ['pending', 'pending'] },
      ],
      distribution: [
        {
          customer_name: 'Safari Hotel',
          items: [{ item_name: 'Potatoes', quantity: 100, unit: 'kg' }],
        },
        {
          customer_name: 'Kilimani School',
          items: [{ item_name: 'Potatoes', quantity: 100, unit: 'kg' }],
        },
      ],
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Safari Hotel')).toBeInTheDocument();
      expect(screen.getByText('Kilimani School')).toBeInTheDocument();
    });
  });

  it('shows empty state when no data for selected date', async () => {
    mockGetDashboard.mockResolvedValue({
      date: '2024-01-15',
      master_procurement: [],
      distribution: [],
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('No data for selected date')).toBeInTheDocument();
    });
  });
});
