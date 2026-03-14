'use client'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Leaf, Scale, Zap, Recycle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { apiClient, queryKeys } from '@/lib/api'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { useEngineering } from '@/lib/engineeringContext'

interface LCAProps {
  className?: string
}

export function LCA({ className = '' }: LCAProps) {
  const { partType, geometryData, material, thickness, quantity } = useEngineering();
  const { data: lcaData, isLoading, error } = useQuery({
    queryKey: queryKeys.partLCA,
    queryFn: () =>
      partType && geometryData && material && thickness && quantity
        ? apiClient.getLCAData({
          part_type: partType,
          geometry_data: geometryData,
          material: material,
          thickness: thickness,
          quantity: quantity,
        })
        : Promise.reject(new Error('Missing part data')),
    enabled: Boolean(partType && geometryData && material && thickness && quantity),
    refetchOnWindowFocus: false,
    retry: 1,
  })

  const getCO2Color = (footprint: number) => {
    if (footprint <= 1) return 'text-green-600 dark:text-green-400'
    if (footprint <= 5) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getRecyclabilityColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400'
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  // Chart colors for donut chart
  const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#6b7280']

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Leaf className="w-5 h-5" />
            Environmental Impact
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Leaf className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">Unable to calculate impact</p>
            <p className="text-xs mt-1">Generate a part first</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Leaf className="w-5 h-5" />
          Environmental Impact
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-6 bg-muted rounded animate-pulse" />
            <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
            <div className="h-4 bg-muted rounded animate-pulse w-1/2" />
          </div>
        ) : lcaData ? (
          <>
            {/* Carbon Footprint */}
            <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-lg">
                  <Leaf className="w-4 h-4 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <div className="text-sm font-medium">Carbon Footprint</div>
                  <div className="text-xs text-muted-foreground">
                    CO₂ equivalent
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className={`text-xl font-bold ${getCO2Color(lcaData.carbon_footprint || 0)}`}>
                  {lcaData.carbon_footprint?.toFixed(2) || '0.00'} <span className="text-sm font-normal">kg CO₂</span>
                </div>
              </div>
            </div>

            {/* Material Mass */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center gap-2">
                <Scale className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium">Material Mass</span>
              </div>
              <div className="text-right">
                <div className="font-bold">
                  {lcaData.material_mass?.toFixed(3) || '0.000'} <span className="text-sm font-normal">kg</span>
                </div>
              </div>
            </div>

            {/* Energy Consumption */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium">Energy Consumption</span>
              </div>
              <div className="text-right">
                <div className="font-bold">
                  {lcaData.energy_consumption?.toFixed(1) || '0.0'} <span className="text-sm font-normal">kWh</span>
                </div>
              </div>
            </div>

            {/* Recyclability Score */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Recycle className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Recyclability</span>
                </div>
                <span className={`text-sm font-bold ${getRecyclabilityColor(lcaData.recyclability_score || 0)}`}>
                  {lcaData.recyclability_score || 0}%
                </span>
              </div>
              <Progress value={lcaData.recyclability_score || 0} className="h-2" />
            </div>

            {/* Impact Breakdown Donut Chart */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Impact Breakdown</h4>
              <div className="h-32">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Material', value: lcaData.carbon_footprint * 0.6 },
                        { name: 'Manufacturing', value: lcaData.carbon_footprint * 0.25 },
                        { name: 'Transport', value: lcaData.carbon_footprint * 0.1 },
                        { name: 'End of Life', value: lcaData.carbon_footprint * 0.05 }
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={25}
                      outerRadius={50}
                      dataKey="value"
                    >
                      {[0, 1, 2, 3].map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) => [`${value?.toFixed(2) || '0.00'} kg CO₂`, 'Impact']}
                      labelStyle={{ color: 'hsl(var(--foreground))' }}
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '6px'
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Legend */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                {[
                  { name: 'Material', color: COLORS[0] },
                  { name: 'Manufacturing', color: COLORS[1] },
                  { name: 'Transport', color: COLORS[2] },
                  { name: 'End of Life', color: COLORS[3] }
                ].map((item, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-muted-foreground">{item.name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommendations */}
            <div className="pt-4 border-t">
              {lcaData.carbon_footprint > 5 && (
                <div className="p-3 bg-orange-50 dark:bg-orange-950/20 border border-orange-200 dark:border-orange-800 rounded-lg mb-2">
                  <div className="text-sm">
                    <div className="font-medium text-orange-800 dark:text-orange-200">High Carbon Footprint</div>
                    <div className="text-orange-600 dark:text-orange-400 text-xs mt-1">
                      Consider using recycled materials or reducing part thickness.
                    </div>
                  </div>
                </div>
              )}

              {lcaData.recyclability_score < 60 && (
                <div className="p-3 bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <div className="text-sm">
                    <div className="font-medium text-yellow-800 dark:text-yellow-200">Low Recyclability</div>
                    <div className="text-yellow-600 dark:text-yellow-400 text-xs mt-1">
                      Choose materials with better end-of-life options.
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Leaf className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">No LCA data available</p>
            <p className="text-xs mt-1">Generate a part to see environmental impact</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
