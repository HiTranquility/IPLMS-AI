import { useEffect, useRef } from 'react';
import { useThemeStore } from '@/stores/useThemeStore';
import styles from './StarTechBackground.module.css';

interface Star {
  x: number;
  y: number;
  size: number;
  baseAlpha: number;
  alpha: number;
  twinkleSpeed: number;
  twinklePhase: number;
  vx: number;
  vy: number;
  color: string;
}

interface PulseWave {
  radius: number;
  maxRadius: number;
  alpha: number;
  speed: number;
}

interface Meteor {
  x: number;
  y: number;
  length: number;
  speed: number;
  angle: number;
  alpha: number;
  thickness: number;
}

export function StarTechBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { theme } = useThemeStore();
  const themeRef = useRef(theme);
  themeRef.current = theme;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // jsdom fallback check (critical for vitest unit tests)
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = 0;
    let height = 0;

    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);
    };

    resize();
    window.addEventListener('resize', resize);

    // Initialize stars
    const starCount = Math.min(Math.floor((width * height) / 9000), 120);
    const darkPalette = ['#ffffff', '#bae6fd', '#e0e7ff', '#fef08a', '#c084fc'];
    const lightPalette = ['#0284c7', '#38bdf8', '#818cf8', '#64748b', '#0369a1'];

    const getPalette = () => (themeRef.current === 'light' ? lightPalette : darkPalette);

    const stars: Star[] = [];

    for (let i = 0; i < starCount; i++) {
      const size = Math.random() < 0.85 ? Math.random() * 1.5 + 0.5 : Math.random() * 2 + 1.8;
      const palette = getPalette();
      stars.push({
        x: Math.random() * width,
        y: Math.random() * height,
        size,
        baseAlpha: Math.random() * 0.6 + 0.3,
        alpha: Math.random() * 0.6 + 0.3,
        twinkleSpeed: Math.random() * 0.025 + 0.008,
        twinklePhase: Math.random() * Math.PI * 2,
        vx: (Math.random() - 0.5) * 0.15,
        vy: (Math.random() - 0.5) * 0.15,
        color: palette[Math.floor(Math.random() * palette.length)],
      });
    }

    // Pulse waves (radar / orbital scans)
    const waves: PulseWave[] = [
      { radius: 0, maxRadius: Math.max(width, height) * 0.7, alpha: 0.25, speed: 0.8 },
      { radius: 180, maxRadius: Math.max(width, height) * 0.7, alpha: 0.15, speed: 0.8 },
    ];

    // Meteors (shooting stars)
    const meteors: Meteor[] = [];
    let nextMeteorTime = performance.now() + 2000;

    const spawnMeteor = () => {
      const angle = Math.PI / 4 + (Math.random() - 0.5) * 0.25; // ~45 degrees diagonal
      meteors.push({
        x: Math.random() * width * 0.8,
        y: -30,
        length: Math.random() * 90 + 70,
        speed: Math.random() * 7 + 9,
        angle,
        alpha: 1,
        thickness: Math.random() * 1.2 + 1.2,
      });
    };

    let lastTime = performance.now();

    const render = (time: number) => {
      const dt = Math.max(0, Math.min((time - lastTime) / 16.6, 2));
      lastTime = time;

      ctx.clearRect(0, 0, width, height);
      const isLight = themeRef.current === 'light';

      // Draw radar pulse wave expanding from center
      const centerX = width / 2;
      const centerY = height / 2;

      for (const wave of waves) {
        if (!prefersReducedMotion) {
          wave.radius += wave.speed * dt;
          if (wave.radius > wave.maxRadius || wave.radius < 0) {
            wave.radius = 0;
            wave.alpha = 0.25;
          }
        }
        const safeRadius = Math.max(0.1, wave.radius);
        const currentAlpha = Math.max(0, wave.alpha * (1 - safeRadius / Math.max(1, wave.maxRadius)));
        ctx.beginPath();
        ctx.arc(centerX, centerY, safeRadius, 0, Math.PI * 2);
        ctx.strokeStyle = isLight
          ? `rgba(2, 132, 199, ${currentAlpha * 0.18})`
          : `rgba(56, 189, 248, ${currentAlpha * 0.22})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Constellation connection lines
      const maxDist = 95;
      ctx.lineWidth = 0.6;
      for (let i = 0; i < stars.length; i++) {
        for (let j = i + 1; j < stars.length; j++) {
          const dx = stars[i].x - stars[j].x;
          const dy = stars[i].y - stars[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < maxDist) {
            const lineAlpha = (1 - dist / maxDist) * 0.18 * Math.min(stars[i].alpha, stars[j].alpha);
            ctx.beginPath();
            ctx.moveTo(stars[i].x, stars[i].y);
            ctx.lineTo(stars[j].x, stars[j].y);
            ctx.strokeStyle = isLight
              ? `rgba(2, 132, 199, ${lineAlpha * 0.4})`
              : `rgba(186, 230, 253, ${lineAlpha})`;
            ctx.stroke();
          }
        }
      }

      // Draw & update stars
      for (const star of stars) {
        if (!prefersReducedMotion) {
          star.x += star.vx * dt;
          star.y += star.vy * dt;

          if (star.x < 0) star.x = width;
          if (star.x > width) star.x = 0;
          if (star.y < 0) star.y = height;
          if (star.y > height) star.y = 0;

          star.twinklePhase += star.twinkleSpeed * dt;
          star.alpha = star.baseAlpha + Math.sin(star.twinklePhase) * 0.3;
          star.alpha = Math.max(0.1, Math.min(1, star.alpha));
        }

        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fillStyle = star.color;
        ctx.globalAlpha = star.alpha;
        ctx.fill();

        // Subtle glow for larger stars
        if (star.size > 1.8) {
          ctx.beginPath();
          ctx.arc(star.x, star.y, star.size * 2.5, 0, Math.PI * 2);
          ctx.fillStyle = star.color;
          ctx.globalAlpha = star.alpha * 0.2;
          ctx.fill();
        }
      }

      // Meteors (shooting stars)
      if (!prefersReducedMotion) {
        if (time > nextMeteorTime) {
          spawnMeteor();
          nextMeteorTime = time + Math.random() * 2500 + 2000;
        }

        for (let i = meteors.length - 1; i >= 0; i--) {
          const m = meteors[i];
          const vx = Math.cos(m.angle) * m.speed * dt;
          const vy = Math.sin(m.angle) * m.speed * dt;
          m.x += vx;
          m.y += vy;
          m.alpha -= 0.008 * dt;

          const tailX = m.x - Math.cos(m.angle) * m.length;
          const tailY = m.y - Math.sin(m.angle) * m.length;

          const grad = ctx.createLinearGradient(m.x, m.y, tailX, tailY);
          if (isLight) {
            grad.addColorStop(0, `rgba(2, 132, 199, ${Math.max(0, m.alpha)})`);
            grad.addColorStop(0.3, `rgba(56, 189, 248, ${Math.max(0, m.alpha * 0.6)})`);
            grad.addColorStop(1, 'rgba(2, 132, 199, 0)');
          } else {
            grad.addColorStop(0, `rgba(255, 255, 255, ${Math.max(0, m.alpha)})`);
            grad.addColorStop(0.2, `rgba(56, 189, 248, ${Math.max(0, m.alpha * 0.85)})`);
            grad.addColorStop(1, 'rgba(56, 189, 248, 0)');
          }

          ctx.beginPath();
          ctx.moveTo(tailX, tailY);
          ctx.lineTo(m.x, m.y);
          ctx.strokeStyle = grad;
          ctx.lineWidth = m.thickness;
          ctx.globalAlpha = 1;
          ctx.stroke();

          // Remove completed meteors
          if (m.alpha <= 0 || m.x > width + 100 || m.y > height + 100) {
            meteors.splice(i, 1);
          }
        }
      }

      ctx.globalAlpha = 1;

      if (!prefersReducedMotion) {
        animationFrameId = requestAnimationFrame(render);
      }
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <div className={styles.canvasWrap} aria-hidden>
      {/* Dynamic Animated Canvas with Twinkling Stars & Meteors */}
      <canvas ref={canvasRef} className={styles.canvas} />

      {/* Cybernetic HUD Grid Overlay */}
      <div className={styles.hudGrid} />

      {/* Cosmic Nebula Ambient Glow Auras */}
      <div className={`${styles.nebulaAura} ${styles.aura1}`} />
      <div className={`${styles.nebulaAura} ${styles.aura2}`} />
      <div className={`${styles.nebulaAura} ${styles.aura3}`} />

      {/* High-Tech HUD Viewport Corner Accents */}
      <div className={`${styles.cornerHUD} ${styles.cornerTL}`} />
      <div className={`${styles.cornerHUD} ${styles.cornerTR}`} />
      <div className={`${styles.cornerHUD} ${styles.cornerBL}`} />
      <div className={`${styles.cornerHUD} ${styles.cornerBR}`} />

      {/* Deep Space Station Coordinate & Telemetry */}
      <div className={styles.telemetryHUD}>
        <div className={styles.equalizer}>
          <span className={`${styles.waveBar} ${styles.bar1}`} />
          <span className={`${styles.waveBar} ${styles.bar2}`} />
          <span className={`${styles.waveBar} ${styles.bar3}`} />
          <span className={`${styles.waveBar} ${styles.bar4}`} />
          <span className={`${styles.waveBar} ${styles.bar5}`} />
        </div>
        <div className={styles.telemetryText}>
          <span className={styles.telemetryLine1}>IPLMS::AI-TELEMETRY // LIVE STREAM // QUANTUM SYNC 99.8%</span>
          <span className={styles.telemetryLine2}>
            GEO-ORBITAL // LAT 10.7769° N // LON 106.7009° E<span className={styles.cursorBlink}>_</span>
          </span>
        </div>
      </div>

      <div className={styles.statusIndicator}>
        <span className={styles.beaconDot} />
        <span>NODE::ONLINE</span>
      </div>
    </div>
  );
}

export default StarTechBackground;
