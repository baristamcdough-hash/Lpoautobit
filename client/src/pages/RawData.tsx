import { useState, useEffect, useCallback } from 'react';
import { Loader } from 'lucide-react';
import { getRawData } from '../services/api';
import type { RawDataItem } from '../services/api';

function getTodayString(): string {
  const d = new Date();
  return d.toISOString().split('T')[0];
}

export default function RawData() {
  const [date, setDate] = useState(getTodayString());
  const [data, setData] = useState<RawDataItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getRawData(date);
      setData(result);
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="w-8 h-8 animate-spin text-teal-600" />
      </div>
    );
  }

  return (
    <div className="p-4 max-w-lg mx-auto">
      {/* Date Filter */}
      <div className="mb-4">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white"
        />
      </div>

      {data.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-slate-500 text-base">No data for selected date</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-800 text-left">
                <th className="px-3 py-2 font-semibold text-white">Date</th>
                <th className="px-3 py-2 font-semibold text-white">Item</th>
                <th className="px-3 py-2 font-semibold text-white">Qty</th>
                <th className="px-3 py-2 font-semibold text-white">Unit</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item, index) => (
                <tr
                  key={item.id}
                  className={index % 2 === 0 ? 'bg-white' : 'bg-slate-50'}
                >
                  <td className="px-3 py-2 text-slate-600 whitespace-nowrap">
                    {item.date_extracted}
                  </td>
                  <td className="px-3 py-2 text-slate-800 font-medium">
                    {item.item_name}
                  </td>
                  <td className="px-3 py-2 text-slate-700">
                    {item.quantity}
                  </td>
                  <td className="px-3 py-2 text-slate-600">{item.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
