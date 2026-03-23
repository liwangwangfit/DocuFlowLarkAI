"""
Excel转换器 - 转为JSON供飞书多维表格使用
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from loguru import logger

from .base import BaseConverter, ConversionResult, DocumentType


class ExcelConverter(BaseConverter):
    """Excel转换器 - 转为JSON供飞书多维表格使用"""
    
    def supports(self, doc_type: DocumentType) -> bool:
        return doc_type in [DocumentType.XLS, DocumentType.XLSX]
    
    async def convert(self, file_path: str) -> ConversionResult:
        """
        Excel转换流程:
        1. pandas读取Excel
        2. 解析所有sheet
        3. 转为JSON格式
        4. 生成字段映射
        """
        try:
            # 读取所有sheet
            excel_file = pd.ExcelFile(file_path)
            sheets_data = {}
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # 处理NaN值
                df = df.fillna('')
                
                # 限制行数（飞书多维表格限制）
                MAX_ROWS = 10000
                if len(df) > MAX_ROWS:
                    logger.warning(f"Sheet '{sheet_name}' 行数过多 ({len(df)}), 将截断至 {MAX_ROWS}")
                    df = df.head(MAX_ROWS)
                
                # 生成字段信息
                fields = []
                for col in df.columns:
                    field_type = self._infer_field_type(df[col])
                    fields.append({
                        'name': str(col),
                        'type': field_type,
                        'property': self._get_field_property(field_type)
                    })
                
                sheets_data[sheet_name] = {
                    'records': df.to_dict('records'),
                    'fields': fields,
                    'row_count': len(df),
                    'column_count': len(df.columns)
                }
            
            return ConversionResult(
                success=True,
                content=json.dumps(sheets_data, ensure_ascii=False, indent=2),
                metadata={
                    'source_type': 'excel',
                    'sheet_count': len(excel_file.sheet_names),
                    'sheet_names': excel_file.sheet_names,
                    'total_rows': sum(s['row_count'] for s in sheets_data.values())
                }
            )
            
        except Exception as e:
            logger.error(f"Excel转换失败: {e}")
            return ConversionResult(
                success=False,
                error_message=str(e),
                metadata={'source_type': 'excel'}
            )
    
    def _infer_field_type(self, series) -> str:
        """推断字段类型（飞书多维表格类型）"""
        if pd.api.types.is_integer_dtype(series):
            return 'number'
        elif pd.api.types.is_float_dtype(series):
            return 'number'
        elif pd.api.types.is_datetime64_any_dtype(series):
            return 'datetime'
        elif pd.api.types.is_bool_dtype(series):
            return 'checkbox'
        else:
            # 检查是否是选项类型（唯一值少于20个）
            unique_count = series.nunique()
            if 2 <= unique_count <= 20 and unique_count < len(series) * 0.5:
                return 'select'
            return 'text'
    
    def _get_field_property(self, field_type: str) -> Dict[str, Any]:
        """获取字段属性"""
        properties = {
            'text': {},
            'number': {'formatter': '0'},
            'datetime': {'formatter': 'YYYY/MM/DD'},
            'checkbox': {},
            'select': {'options': []}
        }
        return properties.get(field_type, {})
    
    async def convert_to_bitable_format(self, file_path: str, sheet_name: Optional[str] = None) -> ConversionResult:
        """
        转换为飞书多维表格格式
        
        飞书多维表格API需要特定格式
        """
        try:
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                # 使用第一个sheet
                excel_file = pd.ExcelFile(file_path)
                df = pd.read_excel(file_path, sheet_name=excel_file.sheet_names[0])
            
            df = df.fillna('')
            
            # 生成字段定义
            fields = []
            for col in df.columns:
                field_type = self._infer_field_type(df[col])
                field_def = {
                    'field_name': str(col),
                    'field_type': self._map_to_bitable_type(field_type)
                }
                
                # 选项类型需要添加选项值
                if field_type == 'select':
                    options = [{'name': str(v)} for v in df[col].unique() if v]
                    field_def['property'] = {'options': options}
                
                fields.append(field_def)
            
            # 生成记录
            records = []
            for _, row in df.iterrows():
                record = {'fields': {}}
                for col in df.columns:
                    value = row[col]
                    if pd.isna(value):
                        value = ''
                    elif isinstance(value, pd.Timestamp):
                        value = value.isoformat()
                    record['fields'][str(col)] = value
                records.append(record)
            
            bitable_data = {
                'fields': fields,
                'records': records
            }
            
            return ConversionResult(
                success=True,
                content=json.dumps(bitable_data, ensure_ascii=False),
                metadata={
                    'source_type': 'excel',
                    'target_type': 'bitable',
                    'sheet_name': sheet_name or 'Sheet1',
                    'row_count': len(records),
                    'field_count': len(fields)
                }
            )
            
        except Exception as e:
            logger.error(f"转换为多维表格格式失败: {e}")
            return ConversionResult(
                success=False,
                error_message=str(e)
            )
    
    def _map_to_bitable_type(self, internal_type: str) -> str:
        """映射内部类型到飞书多维表格类型"""
        mapping = {
            'text': 'Text',
            'number': 'Number',
            'datetime': 'DateTime',
            'checkbox': 'Checkbox',
            'select': 'SingleSelect'
        }
        return mapping.get(internal_type, 'Text')
