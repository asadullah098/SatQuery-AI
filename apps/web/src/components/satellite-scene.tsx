"use client";

import Image from "next/image";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useEffect, useRef, useState } from "react";
import orbitFront from "@/assets/hero/orbit-front.png";
import styles from "./satellite-scene.module.css";

const phases = [
  ["01", "Orbital acquisition", "Sensor platform in view"],
  ["02", "Sensor perspective", "Passing above the payload"],
  ["03", "Earth approach", "Resolving land and water"],
  ["04", "Observation ready", "Evidence enters the frame"],
];

const clamp = (value: number) => Math.min(1, Math.max(0, value));

export default function SatelliteScene() {
  const root = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const durationRef = useRef(14.016);
  const targetTimeRef = useRef(0);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReducedMotion(query.matches);
    sync();
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    const scene = root.current;
    const video = videoRef.current;
    const hero = scene?.closest<HTMLElement>(".hero-cinematic");
    if (!scene || !hero || !video) return;

    const syncDuration = () => {
      if (Number.isFinite(video.duration) && video.duration > 0) {
        durationRef.current = video.duration;
      }
      if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
        video.currentTime = reducedMotion ? 0 : targetTimeRef.current;
      }
    };

    const seekToTarget = () => {
      if (
        reducedMotion ||
        video.seeking ||
        video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA
      ) return;

      const delta = Math.abs(video.currentTime - targetTimeRef.current);
      if (delta > 0.025) video.currentTime = targetTimeRef.current;
    };

    video.addEventListener("loadedmetadata", syncDuration);
    video.addEventListener("seeked", seekToTarget);
    syncDuration();

    const render = (progress: number) => {
      const p = clamp(progress);
      const finalSeekableTime = Math.max(0, durationRef.current - 0.04);
      targetTimeRef.current = p * finalSeekableTime;
      seekToTarget();

      const phase = p < 0.25 ? 0 : p < 0.49 ? 1 : p < 0.74 ? 2 : 3;
      scene.dataset.phase = String(phase);
      scene.style.setProperty("--story-progress", p.toFixed(4));
      hero.style.setProperty("--hero-progress", p.toFixed(4));
    };

    render(0);
    if (reducedMotion) {
      return () => {
        video.removeEventListener("loadedmetadata", syncDuration);
        video.removeEventListener("seeked", seekToTarget);
        hero.style.removeProperty("--hero-progress");
      };
    }

    gsap.registerPlugin(ScrollTrigger);
    const trigger = ScrollTrigger.create({
      trigger: hero,
      start: "top top",
      end: "bottom bottom",
      scrub: true,
      invalidateOnRefresh: true,
      onUpdate: (self) => render(self.progress),
    });

    return () => {
      trigger.kill();
      video.removeEventListener("loadedmetadata", syncDuration);
      video.removeEventListener("seeked", seekToTarget);
      hero.style.removeProperty("--hero-progress");
    };
  }, [reducedMotion]);

  return (
    <div className={styles.scene} ref={root} data-phase="0" aria-hidden="true">
      <div className={styles.media}>
        <Image className={styles.poster} src={orbitFront} alt="" fill sizes="100vw" preload />
        <video
          className={styles.video}
          ref={videoRef}
          src="/media/hero/satquery-orbit-scroll.mp4"
          poster={orbitFront.src}
          preload="auto"
          muted
          playsInline
          disablePictureInPicture
          onCanPlay={() => root.current?.setAttribute("data-ready", "true")}
        />
      </div>

      <div className={styles.scrim} />
      <div className={styles.vignette} />
      <div className={styles.atmosphere} />

      <div className={styles.sequenceStatus}>
        <span className={styles.sequenceLabel}>Orbital descent</span>
        <ol className={styles.phaseList}>
          {phases.map(([number, title, detail]) => (
            <li className={styles.phase} key={number}>
              <span>{number}</span>
              <div><strong>{title}</strong><small>{detail}</small></div>
            </li>
          ))}
        </ol>
      </div>

      <div className={styles.scrollGuide}>
        <span>Scroll to descend</span>
        <i><b /></i>
      </div>

      <div className={styles.loadingStatus}><i /><span>Loading orbital sequence</span></div>
    </div>
  );
}
