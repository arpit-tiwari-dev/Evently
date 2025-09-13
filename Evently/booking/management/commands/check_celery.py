from django.core.management.base import BaseCommand
from celery import current_app
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check Celery worker status and connection'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Checking Celery worker status...")
        
        try:
            # Check if Celery app is configured
            app = current_app
            self.stdout.write(f"✅ Celery app loaded: {app.main}")
            
            # Check broker connection
            broker_url = app.conf.broker_url
            self.stdout.write(f"📡 Broker URL: {broker_url}")
            
            # Check result backend
            result_backend = app.conf.result_backend
            self.stdout.write(f"💾 Result backend: {result_backend}")
            
            # Try to inspect active workers
            try:
                inspect = app.control.inspect()
                active_workers = inspect.active()
                
                if active_workers:
                    self.stdout.write(f"✅ Active workers found: {len(active_workers)}")
                    for worker, tasks in active_workers.items():
                        self.stdout.write(f"  - {worker}: {len(tasks)} active tasks")
                else:
                    self.stdout.write("❌ No active workers found!")
                    self.stdout.write("💡 Make sure Celery worker is running: celery -A Evently worker --loglevel=info")
                
            except Exception as e:
                self.stdout.write(f"❌ Could not inspect workers: {str(e)}")
                self.stdout.write("💡 This might indicate Celery worker is not running")
            
            # Check registered tasks
            registered_tasks = list(app.tasks.keys())
            self.stdout.write(f"📋 Registered tasks: {len(registered_tasks)}")
            for task in registered_tasks:
                if 'booking' in task:
                    self.stdout.write(f"  - {task}")
            
        except Exception as e:
            self.stdout.write(f"❌ Error checking Celery: {str(e)}")
            logger.error(f"Celery check failed: {str(e)}", exc_info=True)
