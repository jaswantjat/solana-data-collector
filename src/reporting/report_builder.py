import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
import asyncio
from dataclasses import dataclass
import pandas as pd
import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader
import os
import aiofiles
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ReportConfig:
    template: str
    output_format: str  # html, pdf, json
    schedule: Optional[str] = None  # cron expression
    recipients: Optional[List[str]] = None
    cache_duration: int = 3600
    include_plots: bool = True
    custom_styles: Optional[Dict] = None

class ReportBuilder:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.templates_dir = os.path.join(output_dir, "templates")
        self.reports_dir = os.path.join(output_dir, "reports")
        self.cache_dir = os.path.join(output_dir, "cache")
        
        # Create directories
        for directory in [self.templates_dir, self.reports_dir, self.cache_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)
            
        # Initialize Jinja environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=True
        )
        
        # Store report configurations
        self.report_configs: Dict[str, ReportConfig] = {}
        self.report_cache: Dict[str, Dict] = {}
        
    async def configure_report(
        self,
        report_name: str,
        config: ReportConfig
    ):
        """Configure a report template"""
        self.report_configs[report_name] = config
        
        # Create report template if it doesn't exist
        template_path = os.path.join(self.templates_dir, f"{config.template}.html")
        if not os.path.exists(template_path):
            await self._create_default_template(config.template)
            
    async def _create_default_template(self, template_name: str):
        """Create a default template"""
        default_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }}</title>
            <style>
                {{ custom_styles }}
            </style>
        </head>
        <body>
            <h1>{{ title }}</h1>
            <div class="metadata">
                <p>Generated: {{ generated_at }}</p>
                <p>Time Range: {{ time_range }}</p>
            </div>
            
            {% for section in sections %}
            <div class="section">
                <h2>{{ section.title }}</h2>
                {{ section.content }}
                {% if section.plot %}
                <div class="plot">
                    {{ section.plot }}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </body>
        </html>
        """
        
        template_path = os.path.join(self.templates_dir, f"{template_name}.html")
        async with aiofiles.open(template_path, "w") as f:
            await f.write(default_template)
            
    async def generate_report(
        self,
        report_name: str,
        data: Dict,
        title: str,
        time_range: Optional[str] = None
    ) -> str:
        """Generate a report from data"""
        try:
            config = self.report_configs.get(report_name)
            if not config:
                raise ValueError(f"Report {report_name} not configured")
                
            # Check cache
            cache_key = f"{report_name}:{hash(json.dumps(data))}"
            if cache_key in self.report_cache:
                cache_entry = self.report_cache[cache_key]
                if datetime.now().timestamp() - cache_entry["timestamp"] < config.cache_duration:
                    return cache_entry["report"]
                    
            # Process data into sections
            sections = await self._process_data(data, config)
            
            # Generate plots if needed
            if config.include_plots:
                for section in sections:
                    if "plot_data" in section:
                        section["plot"] = await self._generate_plot(
                            section["plot_data"],
                            section.get("plot_type", "line")
                        )
                        
            # Render template
            template = self.jinja_env.get_template(f"{config.template}.html")
            report = template.render(
                title=title,
                generated_at=datetime.now().isoformat(),
                time_range=time_range,
                sections=sections,
                custom_styles=config.custom_styles
            )
            
            # Save report
            report_path = os.path.join(
                self.reports_dir,
                f"{report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{config.output_format}"
            )
            
            async with aiofiles.open(report_path, "w") as f:
                await f.write(report)
                
            # Cache report
            self.report_cache[cache_key] = {
                "report": report_path,
                "timestamp": datetime.now().timestamp()
            }
            
            return report_path
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise
            
    async def _process_data(
        self,
        data: Dict,
        config: ReportConfig
    ) -> List[Dict]:
        """Process data into report sections"""
        sections = []
        
        for section_name, section_data in data.items():
            section = {
                "title": section_name.replace("_", " ").title(),
                "content": self._format_content(section_data)
            }
            
            if isinstance(section_data, (list, dict)) and config.include_plots:
                section["plot_data"] = section_data
                section["plot_type"] = self._determine_plot_type(section_data)
                
            sections.append(section)
            
        return sections
        
    def _format_content(self, data: Any) -> str:
        """Format data for display"""
        if isinstance(data, (list, dict)):
            return f"<pre>{json.dumps(data, indent=2)}</pre>"
        return str(data)
        
    def _determine_plot_type(self, data: Any) -> str:
        """Determine appropriate plot type for data"""
        if isinstance(data, list):
            if all(isinstance(x, (int, float)) for x in data):
                return "line"
            return "bar"
        elif isinstance(data, dict):
            return "pie"
        return "line"
        
    async def _generate_plot(
        self,
        data: Union[List, Dict],
        plot_type: str
    ) -> str:
        """Generate a plot using plotly"""
        try:
            fig = go.Figure()
            
            if plot_type == "line":
                if isinstance(data, dict):
                    for key, values in data.items():
                        fig.add_trace(go.Scatter(
                            y=values,
                            name=key,
                            mode="lines+markers"
                        ))
                else:
                    fig.add_trace(go.Scatter(
                        y=data,
                        mode="lines+markers"
                    ))
                    
            elif plot_type == "bar":
                if isinstance(data, dict):
                    fig.add_trace(go.Bar(
                        x=list(data.keys()),
                        y=list(data.values())
                    ))
                else:
                    fig.add_trace(go.Bar(y=data))
                    
            elif plot_type == "pie":
                fig.add_trace(go.Pie(
                    labels=list(data.keys()),
                    values=list(data.values())
                ))
                
            # Update layout
            fig.update_layout(
                template="plotly_white",
                margin=dict(l=10, r=10, t=30, b=10)
            )
            
            return fig.to_html(full_html=False)
            
        except Exception as e:
            logger.error(f"Error generating plot: {str(e)}")
            return ""
            
    async def schedule_report(
        self,
        report_name: str,
        data_callback: callable,
        title: str
    ):
        """Schedule a report for periodic generation"""
        config = self.report_configs.get(report_name)
        if not config or not config.schedule:
            raise ValueError(f"Report {report_name} not configured for scheduling")
            
        async def generate_scheduled_report():
            while True:
                try:
                    # Get fresh data
                    data = await data_callback()
                    
                    # Generate report
                    await self.generate_report(
                        report_name,
                        data,
                        title,
                        f"Last {config.cache_duration} seconds"
                    )
                    
                    # Calculate next run time based on cron expression
                    # This is a simplified version - you might want to use a proper cron parser
                    await asyncio.sleep(config.cache_duration)
                    
                except Exception as e:
                    logger.error(f"Error in scheduled report {report_name}: {str(e)}")
                    await asyncio.sleep(60)
                    
        asyncio.create_task(generate_scheduled_report())
        
    async def get_report_history(
        self,
        report_name: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get history of generated reports"""
        try:
            reports = []
            pattern = f"{report_name}_*.{self.report_configs[report_name].output_format}"
            
            for report_file in sorted(
                Path(self.reports_dir).glob(pattern),
                key=os.path.getctime,
                reverse=True
            )[:limit]:
                reports.append({
                    "path": str(report_file),
                    "generated_at": datetime.fromtimestamp(
                        os.path.getctime(report_file)
                    ).isoformat(),
                    "size": os.path.getsize(report_file)
                })
                
            return reports
            
        except Exception as e:
            logger.error(f"Error getting report history: {str(e)}")
            return []
            
    async def cleanup_old_reports(self, days: int = 30):
        """Clean up old reports"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            
            for report_file in Path(self.reports_dir).glob("*"):
                if datetime.fromtimestamp(os.path.getctime(report_file)) < cutoff:
                    os.remove(report_file)
                    
        except Exception as e:
            logger.error(f"Error cleaning up old reports: {str(e)}")
            
class TokenReport(ReportBuilder):
    """Specialized report builder for token reports"""
    
    async def generate_token_report(
        self,
        token_address: str,
        data: Dict
    ) -> str:
        """Generate a token analysis report"""
        config = ReportConfig(
            template="token_report",
            output_format="html",
            include_plots=True,
            custom_styles={
                "body": "font-family: Arial, sans-serif;",
                ".section": "margin: 20px 0;",
                ".plot": "margin: 10px 0;"
            }
        )
        
        await self.configure_report("token_analysis", config)
        
        return await self.generate_report(
            "token_analysis",
            data,
            f"Token Analysis Report - {token_address}",
            "Last 24 hours"
        )
