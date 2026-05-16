import { useState, useEffect, useCallback } from 'react';
import { Check, Download, Loader, RefreshCw } from 'lucide-react';
import { getDashboard, getExportUrl, toggleItemStatus } from '../services/api';
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
        <Loader className="w-8 h-8 animate-spin text-teal-600" />
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
          className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white"
        />
        <button
          onClick={fetchData}
          className="p-2 border border-slate-300 rounded-lg hover:bg-slate-50"
          aria-label="Refresh"
        >
          <RefreshCw className="w-5 h-5 text-slate-600" />
        </button>
        <a
          href={getExportUrl(date)}
          download
          className="p-2 border border-teal-300 rounded-lg hover:bg-teal-50 bg-white"
          aria-label="Download Excel"
        >
          <Download className="w-5 h-5 text-teal-600" />
        </a>
      </div>

      {isEmpty ? (
        <div className="text-center py-12">
          <p className="text-slate-500 text-base">No data for selected date</p>
          <p className="text-slate-400 text-sm mt-1">
            Upload LPO documents to see procurement data here.
          </p>
        </div>
      ) : (
        <>
          {/* Master Procurement Total */}
          <section className="mb-6">
            <h2 className="text-lg font-bold text-slate-800 mb-3">
              Master Procurement Total
            </h2>
            <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
              {data!.master_procurement.map((item, index) => {
                const isChecked = item.item_ids.every((id) =>
                  checkedItems.has(id)
                );
                return (
                  <div
                    key={`${item.item_name}-${index}`}
                    className={`flex items-center px-4 py-3 ${
                      index !== 0 ? 'border-t border-slate-100' : ''
                    }`}
                  >
                    <button
                      onClick={() => handleToggle(item.item_ids, !isChecked)}
                      className={`w-6 h-6 rounded-md border-2 flex items-center justify-center shrink-0 mr-3 transition-colors ${
                        isChecked
                          ? 'bg-teal-600 border-teal-600'
                          : 'border-slate-300'
                      }`}
                    >
                      {isChecked && <Check className="w-4 h-4 text-white" />}
                    </button>
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-sm font-medium ${
                          isChecked
                            ? 'line-through text-slate-400'
                            : 'text-slate-800'
                        }`}
                      >
                        {item.item_name}
                      </p>
                    </div>
                    <div className="text-right shrink-0 ml-2">
                      <span
                        className={`text-sm font-semibold ${
                          isChecked ? 'text-slate-400' : 'text-slate-700'
                        }`}
                      >
                        {item.total_quantity} {item.unit}
                      </span>
                    </div>
                    {isChecked && (
                      <Check className="w-4 h-4 text-teal-500 ml-2 shrink-0" />
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* Distribution Breakdown */}
          <section>
            <h2 className="text-lg font-bold text-slate-800 mb-3">
              Distribution Breakdown
            </h2>
            <div className="space-y-3">
              {data!.distribution.map((entry) => (
                <div
                  key={entry.customer_name}
                  className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden"
                >
                  <div className="bg-slate-800 px-4 py-2 border-b border-slate-700">
                    <h3 className="text-sm font-bold text-white">
                      {entry.customer_name}
                    </h3>
                  </div>
                  <div className="px-4 py-2">
                    {entry.items.map((item, idx) => (
                      <div
                        key={`${item.item_name}-${idx}`}
                        className={`flex justify-between py-1.5 ${
                          idx !== 0 ? 'border-t border-slate-50' : ''
                        }`}
                      >
                        <span className="text-sm text-slate-700">
                          {item.item_name}
                        </span>
                        <span className="text-sm font-medium text-slate-600">
                          {item.quantity} {item.unit}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
