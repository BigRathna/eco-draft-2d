'use client'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity, AlertTriangle, Shield, MapPin } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { apiClient, queryKeys } from '@/lib/api'
import { useEngineering } from '@/lib/engineeringContext'
import { useEffect } from 'react'

interface AnalysisProps {
  className?: string
  trigger?: number
}

export function Analysis({ className = '', trigger = 0 }: AnalysisProps) {
  const { partType, geometryData, material, thickness, loadCases } = useEngineering();

  const { data: analysisData, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.partAnalysis,
    queryFn: () => {
      // Ensure we have valid load_cases with proper structure
      const validLoadCases = loadCases && loadCases.length > 0 
        ? loadCases 
        : [{
            name: 'default_load',
            force_x: 1000,  // 1000 N
            force_y: 500,   // 500 N
            moment: 0,      // No moment
            application_point: null
          }];
      
      return partType && geometryData && material && thickness
        ? apiClient.analyzePart({
          part_type: partType,
          geometry_data: geometryData,
          material: material,
          thickness: thickness,
          load_cases: validLoadCases,
        })
        : Promise.reject(new Error('Missing part data'));
    },
    enabled: Boolean(partType && geometryData && material && thickness && loadCases?.length > 0),
    refetchOnWindowFocus: false,
    retry: 1,
  })
  
  // Refetch when trigger changes (button clicked)
  useEffect(() => {
    if (trigger > 0 && partType && geometryData) {
      refetch()
    }
  }, [trigger, refetch, partType, geometryData])

  const getSafetyFactorColor = (factor: number) => {
    if (factor >= 3) return 'text-green-600 dark:text-green-400'
    if (factor >= 2) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getSafetyFactorBadge = (factor: number) => {
    if (factor >= 3) return { variant: 'default', text: 'Excellent', class: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900 dark:text-green-200' }
    if (factor >= 2) return { variant: 'default', text: 'Acceptable', class: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900 dark:text-yellow-200' }
    return { variant: 'default', text: 'Critical', class: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900 dark:text-red-200' }
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Stress Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">Unable to perform analysis</p>
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
          <Activity className="w-5 h-5" />
          Stress Analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-6 bg-muted rounded animate-pulse" />
            <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
            <div className="h-4 bg-muted rounded animate-pulse w-1/2" />
          </div>
        ) : analysisData ? (
          <>
            {/* Safety Factor */}
            <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-3">
                <Shield className="w-6 h-6 text-muted-foreground" />
                <div>
                  <div className="text-sm font-medium">Safety Factor</div>
                  <div className="text-xs text-muted-foreground">
                    Factor of safety against failure
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className={`text-2xl font-bold ${getSafetyFactorColor(analysisData.safety_factor || 0)}`}>
                  {analysisData.safety_factor?.toFixed(1) || '0.0'}
                </div>
                <Badge
                  variant="outline"
                  className={getSafetyFactorBadge(analysisData.safety_factor || 0).class}
                >
                  {getSafetyFactorBadge(analysisData.safety_factor || 0).text}
                </Badge>
              </div>
            </div>

            {/* Maximum Stress */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <div className="text-sm font-medium">Maximum Stress</div>
                <div className="text-xs text-muted-foreground">
                  Peak von Mises stress
                </div>
              </div>
              <div className="text-right">
                <div className="text-xl font-bold">
                  {analysisData.max_stress?.toFixed(1) || '0.0'} <span className="text-sm font-normal">MPa</span>
                </div>
              </div>
            </div>

            {/* Critical Locations */}
            {analysisData.critical_locations && analysisData.critical_locations.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Critical Stress Locations</h4>
                <div className="space-y-2">
                  {analysisData.critical_locations.slice(0, 3).map((location, index) => (
                    <div key={index} className="flex justify-between items-center p-2 bg-muted/30 rounded text-xs">
                      <span>Location {index + 1}</span>
                      <div className="text-right">
                        <div className="font-mono">
                          ({location.x?.toFixed(1) || '0.0'}, {location.y?.toFixed(1) || '0.0'})
                        </div>
                        <div className="text-muted-foreground">
                          {location.stress?.toFixed(1) || '0.0'} MPa
                        </div>
                      </div>
                    </div>
                  ))}
                  {analysisData.critical_locations.length > 3 && (
                    <div className="text-xs text-muted-foreground text-center">
                      +{analysisData.critical_locations.length - 3} more locations
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Analysis Status */}
            <div className="pt-4 border-t">
              <div className="grid grid-cols-2 gap-4 text-center">
                <div>
                  <div className="text-xs text-muted-foreground">Analysis Type</div>
                  <div className="text-sm font-medium">Linear Static</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Material</div>
                  <div className="text-sm font-medium">Steel (Default)</div>
                </div>
              </div>
            </div>

            {/* Recommendations */}
            {analysisData.safety_factor && analysisData.safety_factor < 2 && (
              <div className="p-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg">
                <div className="flex gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="text-sm">
                    <div className="font-medium text-red-800 dark:text-red-200">Low Safety Factor</div>
                    <div className="text-red-600 dark:text-red-400 text-xs mt-1">
                      Consider increasing part thickness or adding reinforcement features.
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Activity className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">No analysis available</p>
            <p className="text-xs mt-1">Generate a part to see stress analysis</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
