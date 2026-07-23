import { Bar, Doughnut } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend } from 'chart.js';
import type { Distributions, Language } from '@/types/api';
import { t } from '@/lib/i18n';

Chart.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend);

interface Props {
  distributions: Distributions;
  lang: Language;
}

export function Charts({ distributions, lang }: Props) {
  const budget = distributions.budget_by_sector.slice(0, 8);
  const status = distributions.projects_by_status;

  return (
    <div className="charts">
      <div className="card">
        <h2>{t('budgetTitle', lang)}</h2>
        <div className="chart-box">
          <Bar
            data={{
              labels: budget.map(d => d.label.split(' ')[0]),
              datasets: [{
                data: budget.map(d => d.value),
                backgroundColor: '#1B3556',
                borderRadius: 4,
                maxBarThickness: 42,
              }],
            }}
            options={{
              responsive: true, maintainAspectRatio: false,
              animation: { duration: 400 },
              plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (c) => `AED ${c.parsed.y}M` } },
              },
              scales: {
                x: { grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 40 } },
                y: { beginAtZero: true, ticks: { font: { size: 10 } }, grid: { color: '#EFEDE6' } },
              },
            }}
          />
        </div>
      </div>

      <div className="card">
        <h2>{t('statusTitle', lang)}</h2>
        <div className="chart-box">
          <Doughnut
            data={{
              labels: status.map(d => d.label),
              datasets: [{
                data: status.map(d => d.value),
                backgroundColor: ['#1B3556', '#B08A3E', '#5DCAA5', '#E24B4A'],
                borderWidth: 0,
              }],
            }}
            options={{
              responsive: true, maintainAspectRatio: false, cutout: '58%',
              animation: { duration: 400 },
              plugins: {
                legend: { position: 'right', labels: { boxWidth: 10, padding: 12, font: { size: 11 } } },
              },
            }}
          />
        </div>
      </div>
    </div>
  );
}
