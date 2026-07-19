import { useState, useCallback } from 'react';
import { INITIAL_STATE, buildStateForIndex, ALL_STATIONS } from './data/mockMetroData';

import Header from './components/Header';
import OperationalSummary from './components/OperationalSummary';
import MetroRoute from './components/MetroRoute';
import TrainVisualization from './components/TrainVisualization';
import RecommendationPanel from './components/RecommendationPanel';
import DistributionInsight from './components/DistributionInsight';
import LoadMovement from './components/LoadMovement';
import CrowdMonitor from './components/CrowdMonitor';
import OccupancyAnalytics from './components/OccupancyAnalytics';
import DensityMap from './components/DensityMap';
import SimulationControls from './components/SimulationControls';
import SystemPipeline from './components/SystemPipeline';
import PrototypeInfo from './components/PrototypeInfo';

export default function App() {
  const [stationIndex, setStationIndex] = useState(INITIAL_STATE.station.index);
  const simulationState = buildStateForIndex(stationIndex);
  const { station, coaches, recommendation } = simulationState;

  const handleNext = useCallback(() => {
    if (stationIndex < ALL_STATIONS.length - 1) {
      setStationIndex(i => i + 1);
    }
  }, [stationIndex]);

  const handleReset = useCallback(() => {
    setStationIndex(INITIAL_STATE.station.index);
  }, []);

  return (
    <div className="min-h-screen bg-[#F4F7FA]">
      {/* Sticky header */}
      <Header onReset={handleReset} />

      {/* Operational KPI strip */}
      <OperationalSummary station={station} coaches={coaches} recommendation={recommendation} />

      {/* Main content */}
      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 py-5 space-y-5">

        {/* 1. Metro route tracker */}
        <MetroRoute station={station} />

        {/* 2. HERO: Train visualization */}
        <TrainVisualization coaches={coaches} recommendation={recommendation} station={station} />

        {/* 3. Recommendation + Distribution Insight (side by side on wide screens) */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <div className="xl:col-span-2">
            <RecommendationPanel recommendation={recommendation} coaches={coaches} />
          </div>
          <div>
            <DistributionInsight coaches={coaches} />
          </div>
        </div>

        {/* 4. Load Movement + Crowd Monitor (side by side) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <LoadMovement coaches={coaches} station={station} />
          <CrowdMonitor coaches={coaches} recommendation={recommendation} station={station} />
        </div>

        {/* 5. Analytics + Density Map + Simulation Controls */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <div className="xl:col-span-2">
            <OccupancyAnalytics coaches={coaches} />
          </div>
          <div className="space-y-5">
            <DensityMap coaches={coaches} />
            <SimulationControls station={station} onNext={handleNext} onReset={handleReset} />
          </div>
        </div>

        {/* 6. System pipeline */}
        <SystemPipeline />

        {/* 7. Prototype info */}
        <PrototypeInfo />

        {/* Footer */}
        <footer className="text-center py-4 text-[10px] text-slate-400 font-medium border-t border-slate-200">
          SmartMetro · Intelligent Metro Crowd Management System · Phase 1 Software Prototype · Academic Project
        </footer>
      </main>
    </div>
  );
}
