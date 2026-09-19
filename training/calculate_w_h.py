def conv_output_size(image_size, kernel_size, stride, padding):
    return ((image_size + 2 * padding - kernel_size) / stride) + 1


if __name__ == "__main__":
    # ====== CHỈNH Ở ĐÂY ======
    H = W = 16
    K = 1
    S = 1
    P = 0
    # =========================

    out_h = conv_output_size(H, K, S, P)
    out_w = conv_output_size(W, K, S, P)

    print("=== CONV OUTPUT SIZE ===")
    print(f"Input:  ({H}, {W})")
    print(f"Kernel: {K}, Stride: {S}, Padding: {P}")
    print(f"Output: ({out_h}, {out_w})")