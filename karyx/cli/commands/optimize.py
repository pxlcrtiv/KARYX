import click
from pathlib import Path
from karyx.pipeline import OptimizationPipeline, OptimizationRequest
from karyx.licensing import get_license_manager

# Free forever under MIT. IL5/IL6 (commercial security features) require a
# license; if absent we fall back to IL4 instead of crashing. The audit log
# and air-gap package are still produced at IL4 (open-source path).
COMMERCIAL_LEVELS = {"IL5", "IL6"}


def print_license_banner() -> None:
    """Print license status at CLI startup (truthful — no third-party claims)."""
    watermark = get_license_manager().get_watermark()
    status = watermark["license_status"]
    if status == "UNLICENSED":
        click.echo("")
        click.echo("=" * 60)
        click.echo("  UNLICENSED KARYX OUTPUT")
        click.echo("  This package is NOT accredited for government production.")
        click.echo("  License required: 38929261+pxlcrtiv@users.noreply.github.com")
        click.echo("=" * 60)
        click.echo("")
    elif status == "EVALUATION":
        days = watermark.get("evaluation_expiry", 0)
        click.echo(f"[*] Evaluation mode: {days} days remaining")
        click.echo("[*] Purchase license: 38929261+pxlcrtiv@users.noreply.github.com")
        click.echo("")


@click.command()
@click.option("--model", required=True, help="Path to input model (.pt, .onnx)")
@click.option("--target", help="Target hardware (jetson-nano, jetson-xavier, xilinx-zynq, generic-arm)")
@click.option("--precision", default="INT8", help="Quantization precision (FP16, INT8, INT4)")
@click.option("--calibration-data", help="Path to calibration dataset (for INT8)")
@click.option("--security-level", default="IL4", help="Target security level (IL4, IL5, IL6)")
def optimize(model, target, precision, calibration_data, security_level):
    """Optimize a model for specified hardware."""
    print_license_banner()

    effective_level = security_level
    if security_level in COMMERCIAL_LEVELS:
        manager = get_license_manager()
        status = manager.validate_license()
        if not status["valid"]:
            click.echo(f"[!] {security_level} features require a commercial license.")
            click.echo(f"[!] {status['message']}")
            click.echo("[*] Continuing with IL4 (open-source) features only.")
            effective_level = "IL4"
        elif status["mode"] == "evaluation":
            click.echo(
                f"[*] {security_level} features active (evaluation). "
                f"{status['days_remaining']} days remaining."
            )
        else:
            click.echo("[+] Commercial license validated. Full features enabled.")

    req = OptimizationRequest(
        model_path=Path(model),
        target=target,
        precision=precision,
        calibration_data=Path(calibration_data) if calibration_data else None,
        security_level=effective_level,
    )
    bundle = OptimizationPipeline().run(req)
    click.echo(f"[+] Package created: {bundle.package_path}")
    click.echo(f"[+] Final Chain Hash: {bundle.audit_hash}")
    click.echo("[+] Optimization pipeline finished.")
