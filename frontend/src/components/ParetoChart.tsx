'use client'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { TrendingUp, Play, RefreshCw } from 'lucide-react'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient, queryKeys, OptimizationPoint } from '@/lib/api'
import { toast } from 'sonner'
import { useState, useEffect } from 'react'
import { getCurrentPart } from '@/lib/nlp'

interface ParetoChartProps {
  className?: string
  trigger?: number
  onApplySolution?: (intent: string) => void
}

export function ParetoChart({ className = '', trigger = 0, onApplySolution }: ParetoChartProps) {
  const [selectedPoint, setSelectedPoint] = useState<OptimizationPoint | null>(null)

  const {
    data: optimizationData,
    isLoading: isLoadingOptimization,
    error: optimizationError
  } = useQuery({
    queryKey: queryKeys.optimization,
    queryFn: () => {
      const part = getCurrentPart();
      if (!part) throw new Error('No part context available for optimization');
      return apiClient.runOptimization(part.part_type, part.parameters, ['mass', 'cost'])
    },
    enabled: false, // Don't auto-run, only when triggered
    refetchOnWindowFocus: false,
    retry: 1
  })

  const queryClient = useQueryClient()

  const runOptimizationMutation = useMutation({
    mutationFn: (objectives: string[] = ['mass', 'cost']) => {
      const part = getCurrentPart();
      if (!part) throw new Error('No part context to optimize');
      return apiClient.runOptimization(part.part_type, part.parameters, objectives);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.optimization, data)
      toast.success(`Found ${data.points.length} optimization solutions`)
    },
    onError: (error) => {
      toast.error('Optimization failed: ' + error.message)
    }
  })

  const handleRunOptimization = () => {
    runOptimizationMutation.mutate(['mass', 'cost'])
  }

  // Refetch when trigger changes (button clicked from parent action)
  useEffect(() => {
    if (trigger > 0) {
      handleRunOptimization()
    }
  }, [trigger])

  // Prepare data for scatter plot
  const chartData = optimizationData?.points.map((point, index) => ({
    x: point.objectives.mass,
    y: point.objectives.cost,
    strength: point.objectives.strength,
    carbon: point.objectives.carbon_footprint,
    parameters: point.parameters,
    isParetoOptimal: optimizationData.pareto_optimal.includes(index),
    index
  })) || []

  const paretoOptimalData = chartData.filter(p => p.isParetoOptimal)
  const nonOptimalData = chartData.filter(p => !p.isParetoOptimal)

  // Custom tooltip component
  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: Record<string, unknown> }> }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
          <div className="text-sm font-medium mb-2">
            {data.isParetoOptimal ? '🏆 Pareto Optimal' : 'Sub-optimal'}
          </div>
          <div className="space-y-1 text-xs">
            <div>Mass: {(data.x as number).toFixed(2)} kg</div>
            <div>Cost: ${(data.y as number).toFixed(2)}</div>
            <div>Strength: {(data.strength as number).toFixed(1)} MPa</div>
            <div>CO₂: {(data.carbon as number).toFixed(2)} kg</div>
          </div>
          <div className="mt-2 pt-2 border-t text-xs text-muted-foreground">
            Click to view parameters
          </div>
        </div>
      )
    }
    return null
  }

  // Handle point click
  const handlePointClick = (data: Record<string, unknown>) => {
    if (data && data.payload) {
      const payload = data.payload as Record<string, unknown>
      const point = optimizationData?.points[payload.index as number]
      if (point) {
        setSelectedPoint(point)
      }
    }
  }

  const isLoading = isLoadingOptimization || runOptimizationMutation.isPending

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Optimization Results
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRunOptimization}
              disabled={isLoading}
            >
              {isLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {isLoading ? 'Optimizing...' : 'Run Optimization'}
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-4 bg-muted rounded animate-pulse" />
            <div className="h-32 bg-muted rounded animate-pulse" />
            <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
          </div>
        ) : optimizationData && chartData.length > 0 ? (
          <>
            {/* Pareto Front Chart */}
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--muted))" />
                  <XAxis
                    type="number"
                    dataKey="x"
                    name="Mass"
                    unit="kg"
                    domain={['auto', 'auto']}
                    tick={{ fontSize: 12 }}
                    label={{ value: 'Mass (kg)', position: 'insideBottom', offset: -10 }}
                  />
                  <YAxis
                    type="number"
                    dataKey="y"
                    name="Cost"
                    unit="$"
                    domain={['auto', 'auto']}
                    tick={{ fontSize: 12 }}
                    label={{ value: 'Cost ($)', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip content={<CustomTooltip />} />

                  {/* Non-optimal points */}
                  <Scatter
                    name="Sub-optimal"
                    data={nonOptimalData}
                    fill="hsl(var(--muted-foreground))"
                    fillOpacity={0.6}
                    stroke="hsl(var(--muted-foreground))"
                    strokeWidth={1}
                    onClick={handlePointClick}
                  />

                  {/* Pareto optimal points */}
                  <Scatter
                    name="Pareto Optimal"
                    data={paretoOptimalData}
                    fill="hsl(var(--primary))"
                    stroke="hsl(var(--primary-foreground))"
                    strokeWidth={2}
                    onClick={handlePointClick}
                  />
                </ScatterChart>
              </ResponsiveContainer>
            </div>

            {/* Statistics */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t">
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">
                  {paretoOptimalData.length}
                </div>
                <div className="text-xs text-muted-foreground">Pareto Optimal</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-muted-foreground">
                  {nonOptimalData.length}
                </div>
                <div className="text-xs text-muted-foreground">Sub-optimal</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {chartData.length}
                </div>
                <div className="text-xs text-muted-foreground">Total Solutions</div>
              </div>
            </div>

            {/* Selected Point Details */}
            {selectedPoint && (
              <div className="p-3 bg-muted/50 rounded-lg space-y-2">
                <h4 className="text-sm font-medium">Selected Solution</h4>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <div className="text-muted-foreground">Objectives</div>
                    <div>Mass: {selectedPoint.objectives.mass.toFixed(2)} kg</div>
                    <div>Cost: ${selectedPoint.objectives.cost.toFixed(2)}</div>
                    <div>Strength: {selectedPoint.objectives.strength.toFixed(1)} MPa</div>
                    <div>CO₂: {selectedPoint.objectives.carbon_footprint.toFixed(2)} kg</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Parameters</div>
                    {Object.entries(selectedPoint.parameters).map(([key, value]) => (
                      <div key={key}>
                        {key}: {typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
                      </div>
                    ))}
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full mt-2"
                  onClick={() => {
                    const intentStr = `Change the parameters to: ${Object.entries(selectedPoint.parameters).map(([k,v]) => `${k}=${v}`).join(', ')}`;
                    onApplySolution?.(intentStr);
                    setSelectedPoint(null);
                  }}
                >
                  Apply This Solution
                </Button>
              </div>
            )}

            {/* Legend */}
            <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-primary"></div>
                <span>Pareto Optimal</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-muted-foreground opacity-60"></div>
                <span>Sub-optimal</span>
              </div>
            </div>
          </>
        ) : optimizationError ? (
          <div className="text-center py-8 text-muted-foreground">
            <TrendingUp className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">Unable to run optimization</p>
            <p className="text-xs mt-1">Generate a part first</p>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <TrendingUp className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">No optimization results</p>
            <p className="text-xs mt-1">Click &quot;Run Optimization&quot; to explore design trade-offs</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
