/// <reference lib="webworker" />
import { SyntheticHost, type HostRequest } from "./host";

const host = new SyntheticHost((r) => (self as unknown as DedicatedWorkerGlobalScope).postMessage(r), true);
self.onmessage = (ev: MessageEvent<HostRequest>) => host.handle(ev.data);
