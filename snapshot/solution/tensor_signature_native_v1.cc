// CPU-only exact metadata fingerprint. It never dereferences tensor data.
#include <Python.h>
#include <torch/csrc/autograd/python_variable.h>
#include <torch/csrc/DynamicTypes.h>
#include <c10/core/DeviceType.h>
#include <cstdint>
#include <cstring>
#include <string>
#include <stdexcept>

static void word(std::string& out, uint64_t value) {
  for (int i = 0; i != 8; ++i) out.push_back(char((value >> (8*i)) & 255));
}
static PyObject* encode(PyObject*, PyObject* sequence) {
  PyObject* values = PySequence_Fast(sequence, "Expected a sequence of exact Tensor/Parameter objects");
  if (!values) return nullptr;
  try {
    const auto count = PySequence_Fast_GET_SIZE(values);
    std::string out("CTSIG1\0\0", 8);
    out.reserve(16 + count * 160);
    word(out, count);
    for (Py_ssize_t i = 0; i < count; ++i) {
      PyObject* obj = PySequence_Fast_GET_ITEM(values, i);
      // Tensor subclasses may override Python metadata semantics: decline them.
      if (!THPVariable_CheckExact(obj))
        throw std::runtime_error("Unsupported tensor subclass or non-tensor");
      const auto& t = THPVariable_Unpack(obj);
      auto counter = t.unsafeGetTensorImpl()->version_counter();
      if (!counter.enabled()) throw std::runtime_error("Versionless tensor");
      word(out, reinterpret_cast<uintptr_t>(obj));
      word(out, reinterpret_cast<uintptr_t>(t.data_ptr()));
      word(out, counter.current_version());
      word(out, reinterpret_cast<uintptr_t>(torch::getTHPDtype(t.scalar_type())));
      auto device = t.device();
      const auto name = c10::DeviceTypeName(device.type(), true);
      word(out, name.size());
      out.append(name);
      word(out, static_cast<int64_t>(device.index()));
      word(out, t.storage_offset());
      word(out, t.dim());
      for (auto n : t.sizes()) word(out, n);
      for (auto n : t.strides()) word(out, n);
    }
    Py_DECREF(values);
    return PyBytes_FromStringAndSize(out.data(), out.size());
  } catch (const std::exception& error) {
    Py_DECREF(values);
    PyErr_SetString(PyExc_RuntimeError, error.what());
    return nullptr;
  }
}
static PyMethodDef methods[] = {
  {"encode", encode, METH_O, "Encode identity, pointer, version and every guarded metadata field; CPU only."},
  {nullptr, nullptr, 0, nullptr}
};
static PyModuleDef module = {PyModuleDef_HEAD_INIT, "cosmos_tensor_signature_v1", nullptr, -1, methods};
PyMODINIT_FUNC PyInit_cosmos_tensor_signature_v1() { return PyModule_Create(&module); }
