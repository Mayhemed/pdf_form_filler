    def get_processing_report(self) -> Dict[str, Any]:
        """Generate a comprehensive processing report"""
        if not self.processing_history:
            return {"summary": {"total_stages": 0}, "stage_details": [], "performance_metrics": {}}
            
        total_time = sum(r.processing_time for r in self.processing_history)
        successful_stages = [r for r in self.processing_history if r.success]
        
        return {
            "summary": {
                "total_stages": len(self.processing_history),
                "successful_stages": len(successful_stages),
                "total_processing_time": total_time,
                "overall_success": len(successful_stages) == len(self.processing_history)
            },
            "stage_details": [
                {
                    "stage": r.stage.value,
                    "success": r.success,
                    "processing_time": r.processing_time,
                    "data_points": len(r.data),
                    "errors": r.errors,
                    "avg_confidence": sum(r.confidence_scores.values()) / len(r.confidence_scores) if r.confidence_scores else 0.0
                }
                for r in self.processing_history
            ],
            "performance_metrics": {
                "avg_stage_time": total_time / len(self.processing_history) if self.processing_history else 0,
                "bottleneck_stage": max(self.processing_history, key=lambda r: r.processing_time).stage.value if self.processing_history else None
            }
        }
