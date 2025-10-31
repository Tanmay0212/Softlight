# cli.py - Command Line Interface for Two-Agent System
import click
import json
import os
from softlight.main import main
from softlight.dataset.dataset_manager import DatasetManager
from softlight.core.config.env import Settings


@click.group()
def cli():
    """Softlight Two-Agent UI Capture System CLI"""
    pass


@cli.command()
@click.argument('question')
@click.option('--url', required=True, help='Starting URL for the task')
@click.option('--app', default='Unknown', help='Application name for organization')
@click.option('--use-profile', is_flag=True, help='Use existing Chrome profile with logged-in sessions')
def run(question, url, app, use_profile):
    """
    Run a single task with the two-agent system.
    
    Examples:
        python -m softlight.cli run "Search for Softlight on Google" --url "https://www.google.com/" --app Google
        
        python -m softlight.cli run "How do I create a project in Linear?" --url "https://linear.app/..." --app Linear --use-profile
    """
    click.echo(f"\n{'='*70}")
    click.echo(f"Running task: {question}")
    click.echo(f"URL: {url}")
    click.echo(f"App: {app}")
    click.echo(f"Using separate profile: {use_profile}")
    click.echo(f"{'='*70}\n")
    
    if use_profile:
        click.echo("ℹ️  Using separate Chrome profile - your main Chrome can stay open!")
        click.echo("   First run: Log into the site manually when browser opens")
        click.echo("   Future runs: Login will be remembered\n")
    
    try:
        dataset_path = main(question, url, app, use_profile=use_profile)
        if dataset_path:
            click.echo(f"\n✅ Success! Dataset saved to: {dataset_path}")
        else:
            click.echo(f"\n⚠️  Task did not complete successfully")
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        raise


@cli.command()
@click.option('--tasks', 
              default='examples/task_questions.json', 
              help='Path to tasks JSON file')
@click.option('--use-profile', is_flag=True, help='Use existing Chrome profile for all tasks')
def batch(tasks, use_profile):
    """
    Run multiple tasks from a JSON configuration file.
    
    Examples:
        python -m softlight.cli batch --tasks examples/task_questions.json
        
        python -m softlight.cli batch --tasks examples/task_questions.json --use-profile
    """
    if not os.path.exists(tasks):
        click.echo(f"❌ Tasks file not found: {tasks}", err=True)
        return
    
    try:
        with open(tasks, 'r') as f:
            data = json.load(f)
        
        task_list = data.get('tasks', [])
        total = len(task_list)
        
        click.echo(f"\n{'='*70}")
        click.echo(f"Batch Processing: {total} tasks")
        click.echo(f"Using separate profile: {use_profile}")
        click.echo(f"{'='*70}\n")
        
        if use_profile:
            click.echo("ℹ️  Using separate Chrome profile - your main Chrome can stay open!")
            click.echo("   Login will be remembered across all tasks\n")
        
        completed = 0
        failed = 0
        
        for idx, task in enumerate(task_list, 1):
            click.echo(f"\n{'─'*70}")
            click.echo(f"Task {idx}/{total}: {task['question']}")
            click.echo(f"{'─'*70}\n")
            
            try:
                # Check if task specifies use_profile, otherwise use command-line flag
                task_use_profile = task.get('use_profile', use_profile)
                
                dataset_path = main(
                    task['question'],
                    task['url'],
                    task.get('app', 'Unknown'),
                    use_profile=task_use_profile
                )
                if dataset_path:
                    click.echo(f"✅ Completed: {dataset_path}")
                    completed += 1
                else:
                    click.echo(f"⚠️  Did not complete")
                    failed += 1
            except Exception as e:
                click.echo(f"❌ Failed: {e}", err=True)
                failed += 1
                continue
        
        click.echo(f"\n{'='*70}")
        click.echo(f"Batch Complete")
        click.echo(f"{'='*70}")
        click.echo(f"Total: {total}")
        click.echo(f"Completed: {completed}")
        click.echo(f"Failed: {failed}")
        click.echo(f"{'='*70}\n")
        
    except Exception as e:
        click.echo(f"❌ Error reading tasks file: {e}", err=True)
        raise


@cli.command()
@click.option('--dataset', 
              default=None,
              help='Dataset directory path (defaults to Settings.DATASET_ROOT)')
@click.option('--output',
              default=None,
              help='Output file for summary (defaults to dataset_root/summary.json)')
def summarize(dataset, output):
    """
    Generate a summary of all captured workflows in the dataset.
    
    Example:
        python -m softlight.cli summarize
        python -m softlight.cli summarize --dataset datasets/ --output summary.json
    """
    dataset_root = dataset or Settings.DATASET_ROOT
    
    if not os.path.exists(dataset_root):
        click.echo(f"❌ Dataset directory not found: {dataset_root}", err=True)
        return
    
    click.echo(f"\n📊 Generating dataset summary...")
    click.echo(f"Dataset root: {dataset_root}\n")
    
    try:
        summary = DatasetManager.create_dataset_summary(dataset_root)
        
        click.echo(f"{'='*70}")
        click.echo(f"Dataset Summary")
        click.echo(f"{'='*70}")
        click.echo(f"Total Workflows: {summary['total_workflows']}")
        click.echo(f"Total Steps: {summary['total_steps']}")
        click.echo(f"Total Duration: {summary['total_duration']:.2f}s")
        click.echo(f"{'='*70}\n")
        
        if summary['workflows']:
            click.echo("Workflows:")
            for wf in summary['workflows']:
                status = "✅" if wf.get('completed') else "⚠️"
                click.echo(f"  {status} {wf['question']}")
                click.echo(f"     App: {wf['app']}, Steps: {wf['steps']}, Duration: {wf['duration']:.2f}s")
        
        summary_path = os.path.join(dataset_root, "dataset_summary.json")
        click.echo(f"\n💾 Summary saved to: {summary_path}\n")
        
    except Exception as e:
        click.echo(f"❌ Error generating summary: {e}", err=True)
        raise


@cli.command()
def version():
    """Show version information"""
    click.echo("Softlight Two-Agent UI Capture System v0.1.0")


if __name__ == '__main__':
    cli()

