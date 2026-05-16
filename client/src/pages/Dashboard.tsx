import { useState, useEffect, useCallback } from 'react';
import { Check, Loader, RefreshCw } from 'lucide-react';
import { getDashboard, toggleItemStatus } from '../services/api';
import type { DashboardData } from '../services/api';

function getTodayString(): string {
  const d = new Date();
  return d.toISOString().split('T')[0];
}

export default function Dashboard() {
  const [date, setDate] = useState(getTodayString());
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set());

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getDashboard(date);
      setData(result);
      // Initialize checked state from backend item statuses
      const checked = new Set<number>();
      result.master_procurement.forEach((item) => {
        item.item_ids.forEach((id, index) => {
          if ((item.item_statuses ?? [])[index] === 'procured') {
            checked.add(id);
          }
        });
      });
      setCheckedItems(checked);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleToggle = async (itemIds: number[], checked: boolean) => {
    const newStatus = checked ? 'procured' : 'pending';
    const newChecked = new Set(checkedItems);
    itemIds.forEach((id) => {
      if (checked) {
        newChecked.add(id);
      } else {
        newChecked.delete(id);
      }
    });
    setCheckedItems(newChecked);

    try {
      await Promise.all(itemIds.map((id) => toggleItemStatus(id, newStatus)));
    } catch {
      // Revert on error
      const reverted = new Set(checkedItems);
      setCheckedItems(reverted);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="w-8 h-8 animate-spin text-green-600" />
      </div>
    );
  }

  const isEmpty =
    !data ||
    (data.master_procurement.length === 0 && data.distribution.length === 0);

  return (
    <div className="p-4 max-w-lg mx-auto">
      {/* Date Picker and Refresh */}
      <div className="flex items-center gap-2 mb-4">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
        />
        <button
          onClick={fetchData}
          className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          aria-label="Refresh"
        >
          <RefreshCw className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {isEmpty ? (
        <div className="text-center py-12">
          <p className="text-gray-500 text-base">No data for selected date</p>
          <p className="text-gray-400 text-sm mt-1">
            Upload LPO documents to see procurement data here.
          </p>
        </div>
      ) : (
        <>
          {/* Master Procurement Total */}
          <section className="mb-6">
            <h2 className="text-lg font-bold text-gray-800 mb-3">
              Master Procurement Total
            </h2>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {data!.master_procurement.map((item, index) => {
                const isChecked = item.item_ids.every((id) =>
                  checkedItems.has(id)
                );
                return (
                  <div
                    key={`${item.item_name}-${index}`}
                    className={`flex items-center px-4 py-3 ${
                      index !== 0 ? 'border-t border-gray-100' : ''
                    }`}
                  >
                    <button
                      onClick={() => handleToggle(item.item_ids, !isChecked)}
                      className={`w-6 h-6 rounded-md border-2 flex items-center justify-center shrink-0 mr-3 transition-colors ${
                        isChecked
                          ? 'bg-green-600 border-green-600'
                          : 'border-gray-300'
                      }`}
                    >
                      {isChecked && <Check className="w-4 h-4 text-white" />}
                    </button>
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-sm font-medium ${
                          isChecked
                            ? 'line-through text-gray-400'
                            : 'text-gray-800'
                        }`}
                      >
                        {item.item_name}
                      </p>
                    </div>
                    <div className="text-right shrink-0 ml-2">
                      <span
                        className={`text-sm font-semibold ${
                          isChecked ? 'text-gray-400' : 'text-gray-700'
                        }`}
                      >
                        {item.total_quantity} {item.unit}
                      </span>
                    </div>
                    {isChecked && (
                      <Check className="w-4 h-4 text-green-500 ml-2 shrink-0" />
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* Distribution Breakdown */}
          <section>
            <h2 className="text-lg font-bold text-gray-800 mb-3">
              Distribution Breakdown
            </h2>
            <div className="space-y-3">
              {data!.distribution.map((entry) => (
                <div
                  key={entry.customer_name}
                  className="bg-white rounded-xl border border-gray-200 overflow-hidden"
                >
                  <div className="bg-green-50 px-4 py-2 border-b border-gray-100">
                    <h3 className="text-sm font-bold text-green-800">
                      {entry.customer_name}
                    </h3>
                  </div>
                  <div className="px-4 py-2">
                    {entry.items.map((item, idx) => (
                      <div
                        key={`${item.item_name}-${idx}`}
                        className={`flex justify-between py-1.5 ${
                          idx !== 0 ? 'border-t border-gray-50' : ''
                        }`}
                      >
                        <span className="text-sm text-gray-700">
                          {item.item_name}
                        </span>
                        <span className="text-sm font-medium text-gray-600">
                          {item.quantity} {item.unit}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Signature */}
          <div className="text-center mt-6 mb-2">
            <p className="text-xs text-gray-300">
              nativecodesdevelopers@gmail.com
            </p>
            <p className="text-xs text-gray-300 mt-1">
              made wt ♥️ by:{' '}
              <a
                href="https://wa.me/254717702563"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-green-400 transition-colors"
              >
                P.oR.iot🍄
              </a>
            </p>
          </div>
        </>
      )}
    </div>
  );
}
