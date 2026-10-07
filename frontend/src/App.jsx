import { useState, useEffect, useCallback } from 'react';
import useLiveData from './hooks/useLiveData';
import { advanceSimulation, getSimulationState, resetSimulation } from './services/api';

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
import LoadingOverlay from './components/LoadingOverlay';
import ErrorBanner from './components/ErrorBanner';
import VisionSection from './components/VisionSection';

export default function App() {
  const [simulationState, setSimulationState] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusMessage, setStatusMessage] = useState('');

  const runRequest = useCallback(async (action, loadingLabel) => {
    setIsLoading(true);
    setError('');
    setStatusMessage(loadingLabel);

    try {
      const data = await action();
      setSimulationState(data);
      setStatusMessage(data.message || '');
    } catch (err) {
      setError(err.message || 'Something went wrong while loading simulation data.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Live vision data (polled). The dashboard never talks to the camera or YOLO directly.
  const { vision, evaluation, offline, refresh: refreshVision } = useLiveData();

  const loadInitialState = useCallback(() => {
    runRequest(getSimulationState, 'Loading simulation state');
  }, [runRequest]);

  useEffect(() => {
    loadInitialState();
  }, [loadInitialState]);

  // In vision/auto mode the coach values change on their own, so re-read them quietly
  // (no loading overlay). Plain simulation mode only changes on button presses.
  const dataSource = simulationState?.data_source;
  useEffect(() => {
    if (!dataSource || dataSource === 'simulation') return undefined;
    const id = setInterval(async () => {
      try {
        const data = await getSimulationState();
        setSimulationState((prev) => ({ ...data, message: prev?.message }));
      } catch {
        /* keep last good state; the error banner is for explicit actions */
      }
    }, 2000);
    return () => clearInterval(id);
  }, [dataSource]);

  const handleNext = useCallback(() => {
    runRequest(advanceSimulation, 'Advancing to next station');
  }, [runRequest]);

  const handleReset = useCallback(() => {
    runRequest(resetSimulation, 'Resetting simulation');
  }, [runRequest]);

  const station = simulationState?.station;
  const coaches = simulationState?.coaches || [];
  const recommendation = simulationState?.recommendation;
  const hasDashboardData = station && coaches.length > 0 && recommendation;

  return (
    <div className="min-h-screen bg-[#F4F7FA]">
      {isLoading && <LoadingOverlay label={statusMessage || 'Syncing simulation state'} />}

      <Header onReset={handleReset} disabled={isLoading} />
      <ErrorBanner message={error} onRetry={loadInitialState} disabled={isLoading} />

      {simulationState && !hasDashboardData && (
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 py-5 space-y-5">
          <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 text-sm font-semibold text-blue-700">
            {simulationState.message || 'Waiting for coach data.'}
          </div>
          <VisionSection vision={vision} evaluation={evaluation} offline={offline} onRefresh={refreshVision} />
        </main>
      )}

      {hasDashboardData && (
        <>
          <OperationalSummary station={station} coaches={coaches} recommendation={recommendation} />

          <main className="max-w-[1600px] mx-auto px-4 sm:px-6 py-5 space-y-5">
            {statusMessage && !isLoading && (
              <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-2 text-xs font-semibold text-blue-700">
                {statusMessage}
              </div>
            )}

            <MetroRoute station={station} />
            <TrainVisualization coaches={coaches} recommendation={recommendation} station={station} />
            <VisionSection vision={vision} evaluation={evaluation} offline={offline} onRefresh={refreshVision} />

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
              <div className="xl:col-span-2">
                <RecommendationPanel recommendation={recommendation} coaches={coaches} />
              </div>
              <DistributionInsight coaches={coaches} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <LoadMovement coaches={coaches} station={station} />
              <CrowdMonitor coaches={coaches} recommendation={recommendation} station={station} />
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
              <div className="xl:col-span-2">
                <OccupancyAnalytics coaches={coaches} />
              </div>
              <div className="space-y-5">
                <DensityMap coaches={coaches} />
                <SimulationControls
                  station={station}
                  onNext={handleNext}
                  onReset={handleReset}
                  disabled={isLoading}
                />
              </div>
            </div>

            <SystemPipeline />
            <PrototypeInfo />

            <footer className="text-center py-4 text-[10px] text-slate-400 font-medium border-t border-slate-200">
              SmartMetro - Intelligent Metro Crowd Management System - Phase 2 Software Prototype - Academic Project
            </footer>
          </main>
        </>
      )}
    </div>
  );
}
