from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "ops" / "systemd" / "rozkalns-cv-stats.service"
TIMER = ROOT / "ops" / "systemd" / "rozkalns-cv-stats.timer"
INSTALLER = ROOT / "scripts" / "install-live-stats-systemd.sh"
GENERATOR = ROOT / "scripts" / "generate-stats.py"
DEPLOY = ROOT / "runner" / "release" / "rozkalns-cv-deploy-main"
RUNTIME = "/home/andris/docker/cv"


class StatsSystemdContractTests(unittest.TestCase):
    def test_service_runs_the_production_runtime_writer_as_andris(self) -> None:
        service = SERVICE.read_text(encoding="utf-8")
        self.assertIn("User=andris", service)
        self.assertIn("Group=andris", service)
        self.assertIn("SupplementaryGroups=docker", service)
        self.assertIn(f"WorkingDirectory={RUNTIME}", service)
        self.assertIn(
            f"ExecStart={RUNTIME}/stats.sh --lock /run/rozkalns-cv-stats/generator.lock",
            service,
        )
        self.assertIn("RuntimeDirectory=rozkalns-cv-stats", service)
        self.assertIn(f"ReadWritePaths={RUNTIME}/html /run/rozkalns-cv-stats", service)
        self.assertIn("NoNewPrivileges=yes", service)

    def test_timer_is_persistent_and_runs_every_minute(self) -> None:
        timer = TIMER.read_text(encoding="utf-8")
        self.assertIn("OnCalendar=*-*-* *:*:00", timer)
        self.assertIn("AccuracySec=1s", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("Unit=rozkalns-cv-stats.service", timer)
        self.assertIn("WantedBy=timers.target", timer)

    def test_generator_and_deploy_agree_on_persistent_runtime_output(self) -> None:
        generator = GENERATOR.read_text(encoding="utf-8")
        deploy = DEPLOY.read_text(encoding="utf-8")
        self.assertIn(
            f'"--output", default="{RUNTIME}/html/stats.json"', generator
        )
        self.assertIn(f"RUNTIME='{RUNTIME}'", deploy)
        self.assertIn("--exclude='stats.json'", deploy)

    def test_installer_replaces_only_legacy_stats_scheduling(self) -> None:
        installer = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("crontab -u \"$CRON_USER\" -l", installer)
        self.assertIn('crontab -u "$CRON_USER" "$cron_after"', installer)
        self.assertIn(f'"{RUNTIME}/stats.sh"', installer)
        self.assertIn('"/home/andris/rozkalns-cv/stats.sh"', installer)
        self.assertIn('"scripts/generate-stats.py"', installer)
        self.assertIn('systemctl enable --now "$TIMER"', installer)
        self.assertIn('systemctl start "$SERVICE"', installer)
        self.assertIn("LIVE_STATS_SYSTEMD_SETUP=PASS", installer)


if __name__ == "__main__":
    unittest.main()
