'use client'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { CheckCircle, AlertTriangle, XCircle, Wrench } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { apiClient, queryKeys, ManufacturabilityCheck } from '@/lib/api'
import { useEngineering } from '@/lib/engineeringContext'
import { useEffect } from 'react'

interface ChecksProps {
  className?: string
  trigger?: number
}

export function Checks({ className = '', trigger = 0 }: ChecksProps) {
  const { partType, geometryData, manufacturingProcess, thickness } = useEngineering();
  const { data: checkData, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.partCheck,
    queryFn: () =>
      partType && geometryData && manufacturingProcess && thickness
        ? apiClient.checkPart({
          part_type: partType,
          geometry_data: geometryData,
          manufacturing_process: manufacturingProcess,
          thickness: thickness,
        })
        : Promise.reject(new Error('Missing part data')),
    enabled: Boolean(partType && geometryData && manufacturingProcess && thickness),
    refetchOnWindowFocus: false,
    retry: 1,
  })
  
  // Refetch when trigger changes (button clicked)
  useEffect(() => {
    if (trigger > 0 && partType && geometryData) {
      refetch()
    }
  }, [trigger, refetch, partType, geometryData])

  const getStatusIcon = (status: ManufacturabilityCheck['status']) => {
    switch (status) {
      case 'pass':
        return <CheckCircle className="w-4 h-4" />
      case 'warning':
        return <AlertTriangle className="w-4 h-4" />
      case 'fail':
        return <XCircle className="w-4 h-4" />
      default:
        return <CheckCircle className="w-4 h-4" />
    }
  }

  const getStatusColor = (status: ManufacturabilityCheck['status']) => {
    switch (status) {
      case 'pass':
        return 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900 dark:text-green-200'
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900 dark:text-yellow-200'
      case 'fail':
        return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900 dark:text-red-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  const getOverallScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400'
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wrench className="w-5 h-5" />
            Manufacturability Check
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <XCircle className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">Unable to perform checks</p>
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
          <Wrench className="w-5 h-5" />
          Manufacturability Check
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-4 bg-muted rounded animate-pulse" />
            <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
            <div className="h-4 bg-muted rounded animate-pulse w-1/2" />
          </div>
        ) : checkData ? (
          <>
            {/* Overall Score */}
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Overall Score</span>
                <span className={`text-lg font-bold ${getOverallScoreColor(checkData.overall_score)}`}>
                  {checkData.overall_score}%
                </span>
              </div>
              <Progress value={checkData.overall_score} className="h-2" />
            </div>

            {/* Individual Checks */}
            <div className="space-y-3">
              <h4 className="text-sm font-medium">Detailed Checks</h4>
              <div className="space-y-2">
                {checkData.checks.map((check, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 p-3 rounded-lg border bg-card"
                  >
                    <Badge
                      variant="outline"
                      className={`${getStatusColor(check.status)} flex items-center gap-1 px-2 py-1`}
                    >
                      {getStatusIcon(check.status)}
                      {check.status?.toUpperCase() || 'UNKNOWN'}
                    </Badge>

                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm">{check.category}</div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {check.message}
                      </div>
                      {check.details && (
                        <div className="text-xs text-muted-foreground mt-1 p-2 bg-muted rounded">
                          {check.details}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Summary Statistics */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t">
              <div className="text-center">
                <div className="text-lg font-bold text-green-600 dark:text-green-400">
                  {checkData.checks.filter(c => c.status === 'pass').length}
                </div>
                <div className="text-xs text-muted-foreground">Passed</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-yellow-600 dark:text-yellow-400">
                  {checkData.checks.filter(c => c.status === 'warning').length}
                </div>
                <div className="text-xs text-muted-foreground">Warnings</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-red-600 dark:text-red-400">
                  {checkData.checks.filter(c => c.status === 'fail').length}
                </div>
                <div className="text-xs text-muted-foreground">Failed</div>
              </div>
            </div>
          </>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Wrench className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">No checks available</p>
            <p className="text-xs mt-1">Generate a part to see manufacturability analysis</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
