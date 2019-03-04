import zstd


def compress(input_data, compressiondict=None):
    if isinstance(input_data, str):
        input_data = input_data.encode('utf-8')

    zstd_compression_level = 22  # Highest (best) compression level is 22
    if compressiondict is None:
        zstandard_compressor = zstd.ZstdCompressor(level=zstd_compression_level)
    else:
        zstandard_compressor = zstd.ZstdCompressor(level=zstd_compression_level, dict_data=compressiondict)
    zstd_compressed_data = zstandard_compressor.compress(input_data)
    return zstd_compressed_data


def decompress(zstd_compressed_data, compressiondict=None):
    if compressiondict is None:
        zstandard_decompressor = zstd.ZstdDecompressor()
    else:
        zstandard_decompressor = zstd.ZstdDecompressor(dict_data=compressiondict)
    uncompressed_data = zstandard_decompressor.decompress(zstd_compressed_data)
    return uncompressed_data
