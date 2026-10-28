import gc
import multiprocessing as mp
from multiprocessing import shared_memory
from time import perf_counter

import numpy as np

N = 10_000_000


def shared_memory_receiver(name, size, connection):
    shm = shared_memory.SharedMemory(name=name)

    try:
        array = np.ndarray(
            (size,),
            dtype=np.int64,
            buffer=shm.buf,
        )

        # Read the data to make sure it is available.
        checksum = int(array.sum())

        connection.send(checksum)

    finally:
        shm.close()
        connection.close()


def pipe_receiver(connection):
    try:
        array = connection.recv()
        checksum = int(array.sum())
        connection.send(checksum)

    finally:
        connection.close()


def benchmark_shared_memory(array, expected_checksum):
    shm = shared_memory.SharedMemory(
        create=True,
        size=array.nbytes,
    )

    receiver = None
    parent_connection = None
    child_connection = None

    try:
        shared_array = np.ndarray(
            array.shape,
            dtype=array.dtype,
            buffer=shm.buf,
        )

        shared_array[:] = array

        parent_connection, child_connection = mp.Pipe()

        receiver = mp.Process(
            target=shared_memory_receiver,
            args=(shm.name, len(array), child_connection),
        )

        start = perf_counter()
        receiver.start()
        child_connection.close()

        checksum = parent_connection.recv()
        receiver.join()

        elapsed = perf_counter() - start

        if receiver.exitcode != 0:
            raise RuntimeError("Shared Memory receiver failed")

        if checksum != expected_checksum:
            raise RuntimeError("Shared Memory checksum mismatch")

        return elapsed

    finally:
        if receiver is not None and receiver.is_alive():
            receiver.terminate()
            receiver.join()

        if parent_connection is not None:
            parent_connection.close()

        if child_connection is not None:
            child_connection.close()

        shm.close()
        shm.unlink()


def benchmark_pipe(array, expected_checksum):
    parent_connection, child_connection = mp.Pipe()

    receiver = mp.Process(
        target=pipe_receiver,
        args=(child_connection,),
    )

    try:
        receiver.start()
        child_connection.close()

        start = perf_counter()

        parent_connection.send(array)
        checksum = parent_connection.recv()

        receiver.join()

        elapsed = perf_counter() - start

        if receiver.exitcode != 0:
            raise RuntimeError("Pipe receiver failed")

        if checksum != expected_checksum:
            raise RuntimeError("Pipe checksum mismatch")

        return elapsed

    finally:
        if receiver.is_alive():
            receiver.terminate()
            receiver.join()

        parent_connection.close()
        child_connection.close()


def main():
    print(f"Array size: {N:,} numbers")
    print(f"Data type: int64")
    print(f"Data size: {N * 8 / (1024 ** 2):.2f} MiB")

    array = np.arange(N, dtype=np.int64)
    expected_checksum = int(array.sum())

    print(f"Expected checksum: {expected_checksum}")

    print("\nTesting Shared Memory...")
    shared_time = benchmark_shared_memory(
        array,
        expected_checksum,
    )

    print("\nTesting Pipe...")
    gc.collect()

    pipe_time = benchmark_pipe(
        array,
        expected_checksum,
    )

    print("\n=== RESULTS ===")
    print(f"Shared Memory: {shared_time:.4f} seconds")
    print(f"Pipe:          {pipe_time:.4f} seconds")

    if shared_time > 0:
        print(f"Pipe / Shared Memory: {pipe_time / shared_time:.2f}x")

    print("\nBoth processes received the correct data.")


if __name__ == "__main__":
    mp.freeze_support()
    main()
