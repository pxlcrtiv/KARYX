import click
from karyx.licensing import check_license


@click.command()
@click.option("--package", required=True, help="Path to package to deploy")
@click.option("--target-host", help="Hostname or IP of target hardware")
def deploy(package, target_host):
    """Deploy package to target hardware."""
    # Commercial feature: gate at the command entry point only.
    check_license("Secure hardware deployment")
    click.echo(f"Deploying {package} to {target_host if target_host else 'local'}")
    # TODO: Implement deployment logic
