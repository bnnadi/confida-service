"""
Report Export Utilities for Confida.

This module provides utilities for exporting analytics reports in various formats
including CSV, PDF, and JSON.
"""
import csv
import io
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from app.models.analytics_models import ReportResponse, PerformanceMetrics, SessionAnalytics, TrendAnalysis
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReportExporter:
    """Utility class for exporting reports in various formats."""
    
    @staticmethod
    def export_csv(report: ReportResponse) -> str:
        """
        Export report as CSV format.
        
        Args:
            report: ReportResponse object to export
            
        Returns:
            CSV string content
        """
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(["Confida Analytics Report"])
            writer.writerow(["Generated:", report.generated_at.isoformat()])
            writer.writerow(["User ID:", report.user_id])
            writer.writerow(["Time Period:", report.time_period])
            writer.writerow([])
            
            # Write performance metrics
            writer.writerow(["Performance Metrics"])
            metrics = report.performance_metrics
            writer.writerow(["Total Sessions", metrics.total_sessions])
            writer.writerow(["Average Score", f"{metrics.average_score:.2f}"])
            writer.writerow(["Improvement Trend", f"{metrics.improvement_trend:.2f}%"])
            writer.writerow(["Completion Rate", f"{metrics.completion_rate:.2f}%"])
            writer.writerow(["Total Questions Answered", metrics.total_questions_answered])
            writer.writerow(["Average Response Time", f"{metrics.average_response_time:.2f}s"])
            writer.writerow([])
            
            # Write strongest areas
            writer.writerow(["Strongest Areas"])
            for area in metrics.strongest_areas:
                writer.writerow([area])
            writer.writerow([])
            
            # Write improvement areas
            writer.writerow(["Areas for Improvement"])
            for area in metrics.improvement_areas:
                writer.writerow([area])
            writer.writerow([])
            
            # Write trend analysis if available
            if report.trend_analysis:
                writer.writerow(["Trend Analysis"])
                trend = report.trend_analysis
                writer.writerow(["Metric", trend.metric])
                writer.writerow(["Trend Direction", trend.trend_direction.value])
                writer.writerow(["Trend Percentage", f"{trend.trend_percentage:.2f}%"])
                writer.writerow(["Confidence Level", f"{trend.confidence_level:.2f}"])
                writer.writerow([])
            
            # Write session details
            writer.writerow(["Session Details"])
            writer.writerow([
                "Session ID", "Role", "Total Questions", "Answered Questions",
                "Average Score", "Completion Time (s)", "Status", "Created At"
            ])
            
            for session in report.sessions:
                writer.writerow([
                    session.session_id,
                    session.role,
                    session.total_questions,
                    session.answered_questions,
                    f"{session.average_score:.2f}",
                    session.completion_time,
                    session.status,
                    session.created_at.isoformat()
                ])
            writer.writerow([])
            
            # Write recommendations
            writer.writerow(["Recommendations"])
            for i, rec in enumerate(report.recommendations, 1):
                writer.writerow([f"{i}. {rec}"])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting report to CSV: {e}")
            raise
    
    @staticmethod
    def export_pdf(report: ReportResponse) -> bytes:
        """
        Export report as PDF format.
        
        Args:
            report: ReportResponse object to export
            
        Returns:
            PDF bytes content
        """
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
            styles = getSampleStyleSheet()
            story = []
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=18,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.darkblue
            )
            
            # Title
            title = Paragraph("Confida Analytics Report", title_style)
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Report metadata
            metadata_data = [
                ["Generated:", report.generated_at.strftime("%Y-%m-%d %H:%M:%S")],
                ["User ID:", report.user_id],
                ["Time Period:", report.time_period],
                ["Report Type:", report.report_type]
            ]
            
            metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
            metadata_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(metadata_table)
            story.append(Spacer(1, 20))
            
            # Performance metrics
            story.append(Paragraph("Performance Metrics", heading_style))
            metrics = report.performance_metrics
            
            metrics_data = [
                ["Metric", "Value"],
                ["Total Sessions", str(metrics.total_sessions)],
                ["Average Score", f"{metrics.average_score:.2f}"],
                ["Improvement Trend", f"{metrics.improvement_trend:.2f}%"],
                ["Completion Rate", f"{metrics.completion_rate:.2f}%"],
                ["Total Questions Answered", str(metrics.total_questions_answered)],
                ["Average Response Time", f"{metrics.average_response_time:.2f}s"]
            ]
            
            metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(metrics_table)
            story.append(Spacer(1, 20))
            
            # Strongest areas
            if metrics.strongest_areas:
                story.append(Paragraph("Strongest Areas", heading_style))
                for area in metrics.strongest_areas:
                    story.append(Paragraph(f"• {area}", styles['Normal']))
                story.append(Spacer(1, 12))
            
            # Improvement areas
            if metrics.improvement_areas:
                story.append(Paragraph("Areas for Improvement", heading_style))
                for area in metrics.improvement_areas:
                    story.append(Paragraph(f"• {area}", styles['Normal']))
                story.append(Spacer(1, 20))
            
            # Trend analysis
            if report.trend_analysis:
                story.append(Paragraph("Trend Analysis", heading_style))
                trend = report.trend_analysis
                
                trend_data = [
                    ["Metric", "Value"],
                    ["Metric Analyzed", trend.metric],
                    ["Trend Direction", trend.trend_direction.value.title()],
                    ["Trend Percentage", f"{trend.trend_percentage:.2f}%"],
                    ["Confidence Level", f"{trend.confidence_level:.2f}"]
                ]
                
                trend_table = Table(trend_data, colWidths=[2.5*inch, 2.5*inch])
                trend_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(trend_table)
                story.append(Spacer(1, 20))
            
            # Session summary
            if report.sessions:
                story.append(Paragraph("Session Summary", heading_style))
                
                # Create session summary table
                session_headers = ["Role", "Questions", "Score", "Time (s)", "Status"]
                session_data = [session_headers]
                
                for session in report.sessions[:10]:  # Limit to first 10 sessions
                    session_data.append([
                        session.role,
                        f"{session.answered_questions}/{session.total_questions}",
                        f"{session.average_score:.1f}",
                        str(session.completion_time),
                        session.status
                    ])
                
                session_table = Table(session_data, colWidths=[1.5*inch, 1*inch, 0.8*inch, 0.8*inch, 1*inch])
                session_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(session_table)
                story.append(Spacer(1, 20))
            
            # Recommendations
            if report.recommendations:
                story.append(Paragraph("Recommendations", heading_style))
                for i, rec in enumerate(report.recommendations, 1):
                    story.append(Paragraph(f"{i}. {rec}", styles['Normal']))
                story.append(Spacer(1, 20))
            
            # Footer
            story.append(Paragraph(
                f"Report generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                styles['Normal']
            ))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting report to PDF: {e}")
            raise
    
    @staticmethod
    def export_json(report: ReportResponse) -> str:
        """
        Export report as JSON format.
        
        Args:
            report: ReportResponse object to export
            
        Returns:
            JSON string content
        """
        try:
            # Convert to dict and add export metadata
            export_data = {
                "export_info": {
                    "exported_at": datetime.utcnow().isoformat(),
                    "format": "json",
                    "version": "1.0.0"
                },
                "report": report.dict()
            }
            
            return json.dumps(export_data, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error exporting report to JSON: {e}")
            raise
    
    @staticmethod
    def export_report(report: ReportResponse, format: str) -> str:
        """
        Export report in the specified format.
        
        Args:
            report: ReportResponse object to export
            format: Export format ('json', 'csv', 'pdf')
            
        Returns:
            Exported content (string for json/csv, bytes for pdf)
        """
        try:
            if format.lower() == "json":
                return ReportExporter.export_json(report)
            elif format.lower() == "csv":
                return ReportExporter.export_csv(report)
            elif format.lower() == "pdf":
                return ReportExporter.export_pdf(report)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting report in format {format}: {e}")
            raise


class ReportTemplate:
    """Template utilities for report generation."""
    
    @staticmethod
    def get_email_template(report: ReportResponse) -> str:
        """
        Generate HTML email template for report.
        
        Args:
            report: ReportResponse object
            
        Returns:
            HTML email content
        """
        try:
            metrics = report.performance_metrics
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
                    .metric {{ margin: 10px 0; }}
                    .metric-label {{ font-weight: bold; }}
                    .recommendations {{ background-color: #e8f4f8; padding: 15px; border-radius: 5px; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Confida Analytics Report</h1>
                    <p><strong>User ID:</strong> {report.user_id}</p>
                    <p><strong>Time Period:</strong> {report.time_period}</p>
                    <p><strong>Generated:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <h2>Performance Summary</h2>
                <div class="metric">
                    <span class="metric-label">Total Sessions:</span> {metrics.total_sessions}
                </div>
                <div class="metric">
                    <span class="metric-label">Average Score:</span> {metrics.average_score:.2f}
                </div>
                <div class="metric">
                    <span class="metric-label">Improvement Trend:</span> {metrics.improvement_trend:.2f}%
                </div>
                <div class="metric">
                    <span class="metric-label">Completion Rate:</span> {metrics.completion_rate:.2f}%
                </div>
                
                <h2>Recommendations</h2>
                <div class="recommendations">
                    <ul>
                        {''.join([f'<li>{rec}</li>' for rec in report.recommendations])}
                    </ul>
                </div>
                
                <div class="footer">
                    <p>This report was generated by Confida Analytics.</p>
                    <p>For more detailed analytics, visit your dashboard.</p>
                </div>
            </body>
            </html>
            """
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error generating email template: {e}")
            raise
    
    @staticmethod
    def get_summary_template(report: ReportResponse) -> Dict[str, Any]:
        """
        Generate summary template for quick overview.
        
        Args:
            report: ReportResponse object
            
        Returns:
            Summary data dictionary
        """
        try:
            metrics = report.performance_metrics
            
            return {
                "summary": {
                    "total_sessions": metrics.total_sessions,
                    "average_score": round(metrics.average_score, 2),
                    "improvement_trend": round(metrics.improvement_trend, 2),
                    "completion_rate": round(metrics.completion_rate, 2)
                },
                "key_insights": {
                    "strongest_areas": metrics.strongest_areas,
                    "improvement_areas": metrics.improvement_areas,
                    "top_recommendations": report.recommendations[:3]  # Top 3 recommendations
                },
                "metadata": {
                    "generated_at": report.generated_at.isoformat(),
                    "time_period": report.time_period,
                    "report_type": report.report_type
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating summary template: {e}")
            raise
