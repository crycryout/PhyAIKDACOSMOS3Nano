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

static PyObject* scan_routes(PyObject*, PyObject* sequence) {
  PyObject* records = PySequence_Fast(sequence, "Expected route records");
  if (!records) return nullptr;
  bool valid = true;
  for (Py_ssize_t i = 0; valid && i < PySequence_Fast_GET_SIZE(records); ++i) {
    PyObject* record = PySequence_Fast_GET_ITEM(records, i);
    if (!PyTuple_CheckExact(record) || PyTuple_GET_SIZE(record) != 7) {
      Py_DECREF(records); PyErr_SetString(PyExc_TypeError, "Malformed route record"); return nullptr;
    }
    PyObject* obj = PyTuple_GET_ITEM(record, 0);
    PyObject* cls = PyTuple_GET_ITEM(record, 1);
    PyObject* saved_dict = PyTuple_GET_ITEM(record, 2);
    if (reinterpret_cast<PyObject*>(Py_TYPE(obj)) != cls || !PyDict_CheckExact(saved_dict)) { valid=false; break; }
    PyObject* actual_dict = PyObject_GetAttrString(obj, "__dict__");
    if (!actual_dict) { Py_DECREF(records); return nullptr; }
    if (actual_dict != saved_dict) valid=false;
    Py_DECREF(actual_dict);
    if (!valid) break;
    const auto revision=PyLong_AsUnsignedLongLong(PyTuple_GET_ITEM(record,3));
    if (PyErr_Occurred()) { Py_DECREF(records); return nullptr; }
    if (reinterpret_cast<PyDictObject*>(saved_dict)->ma_version_tag != revision) {valid=false; break;}
    for (const char* key : {"_forward_hooks","_forward_pre_hooks"}) {
      PyObject* hooks=PyDict_GetItemString(saved_dict,key);
      if (!hooks) {valid=false; break;}
      int nonempty=PyObject_IsTrue(hooks);
      if (nonempty<0) {Py_DECREF(records); return nullptr;}
      if (nonempty) {valid=false; break;}
    }
    if (!valid) break;
    for (int field=4;field<=5;++field) {
      PyObject* actual=PyObject_GetAttrString(cls,field==4?"forward":"_act_and_mul");
      if (!actual) {
        if (!PyErr_ExceptionMatches(PyExc_AttributeError)) {Py_DECREF(records); return nullptr;}
        PyErr_Clear(); actual=Py_NewRef(Py_None);
      }
      valid=actual==PyTuple_GET_ITEM(record,field);
      Py_DECREF(actual);
      if (!valid) break;
    }
    PyObject* registries=PyTuple_GET_ITEM(record,6);
    if (!PyTuple_CheckExact(registries)) {Py_DECREF(records);PyErr_SetString(PyExc_TypeError,"Malformed registry records");return nullptr;}
    for (Py_ssize_t j=0;valid && j<PyTuple_GET_SIZE(registries);++j) {
      PyObject* entry=PyTuple_GET_ITEM(registries,j);
      if (!PyTuple_CheckExact(entry)||PyTuple_GET_SIZE(entry)!=3) {Py_DECREF(records);PyErr_SetString(PyExc_TypeError,"Malformed registry entry");return nullptr;}
      PyObject* key=PyTuple_GET_ITEM(entry,0);
      PyObject* registry=PyTuple_GET_ITEM(entry,1);
      PyObject* actual=PyDict_GetItemWithError(saved_dict,key);
      if (PyErr_Occurred()) {Py_DECREF(records);return nullptr;}
      if (actual!=registry || !PyDict_CheckExact(registry)) {valid=false;break;}
      auto old_revision=PyLong_AsUnsignedLongLong(PyTuple_GET_ITEM(entry,2));
      if (PyErr_Occurred()) {Py_DECREF(records);return nullptr;}
      if (reinterpret_cast<PyDictObject*>(registry)->ma_version_tag!=old_revision) valid=false;
    }
  }
  Py_DECREF(records);
  return PyBool_FromLong(valid);
}

static PyMethodDef methods[] = {
  {"scan_routes", scan_routes, METH_O, "Validate every route dictionary, registry, class and hook; CPU only."},
  {"encode", encode, METH_O, "Encode identity, pointer, version and every guarded metadata field; CPU only."},
  {nullptr, nullptr, 0, nullptr}
};
static PyModuleDef module = {PyModuleDef_HEAD_INIT, "cosmos_tensor_signature_v2", nullptr, -1, methods};
PyMODINIT_FUNC PyInit_cosmos_tensor_signature_v2() { return PyModule_Create(&module); }
